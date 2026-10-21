from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io
from datetime import datetime

from app import models, schemas
from app.api import deps
from app.core.ehr_validator import validate_ehr_format
from app.core.password_validator import validate_password_strength
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user, remove_role_for_user, get_roles_for_user, get_permissions_for_role
from app.services.user_service import UserService as user_service

router = APIRouter()

# 员工导入模板列 (2026-10-16 决策 2): 4 列全必填
#   EHR 号  登录标识 (auth.py:25 authenticate_user(ehr_id=...)), 7 位数字唯一
#   姓名    与系统已有姓名冲突时报错, 不静默覆盖
#   组别    按组名匹配; 匹配不到整行失败, 不静默留空 (原实现 team_id 匹配不到
#           就留 None, 员工成了无组孤儿 —— Rule 12 静默降级)
#   初始密码 管理员逐个填, 必须含大小写+数字+特殊字符且 ≥8 位
_USER_IMPORT_COLUMNS = {
    "EHR号": "ehr_id",
    "ehr_id": "ehr_id",
    "姓名": "name",
    "name": "name",
    "组别": "team_name",
    "team_name": "team_name",
    "初始密码": "password",
    "password": "password",
}


def _resolve_user_import_columns(df) -> Dict[str, str]:
    """把 Excel 表头映射成内部字段名。

    中文列名是模板的主形态 (与家访/培训模板一致), 同时接受英文别名,
    兼容既有调用方。

    Returns:
        {内部字段名: 实际列名}, 键恒为 ehr_id / name / team_name / password
    Raises:
        HTTPException 400: 缺必填列, 消息列出**全部**缺失项
    """
    resolved: Dict[str, str] = {}
    for col in df.columns:
        field = _USER_IMPORT_COLUMNS.get(str(col).strip())
        if field:
            resolved[field] = col

    # 注意比对的是**内部字段名** (resolved 的键), 不是中文表头 —— 两者只有
    # name 恰好同名, 用中文去查会把另外 3 列全报成缺失。
    required = {
        "ehr_id": "EHR号",
        "name": "姓名",
        "team_name": "组别",
        "password": "初始密码",
    }
    missing = [label for field, label in required.items() if field not in resolved]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"缺少必要的列: {', '.join(missing)} "
                f"(模板共 4 列: EHR号 / 姓名 / 组别 / 初始密码)"
            ),
        )
    return resolved


@router.get("/", response_model=schemas.PaginatedResponse[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 1000,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户列表
    """
    # 权限: 与本文件其余端点一致 (read_user / create_user / update_user 都做了这层校验)。
    # 此处原先漏检, 导致任意登录员工可拉取全行用户 + 密码哈希。
    if not deps.check_permissions("user", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")

    users = db.query(models.User).offset(skip).limit(limit).all()
    total = db.query(models.User).count()
    
    # 获取每个用户的角色
    for user in users:
        user.roles = get_roles_for_user(str(user.id))
    
    return {
        "items": users,
        "total": total,
        "page": skip // limit + 1,
        "size": limit
    }


@router.post("/", response_model=schemas.User, status_code=201)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新用户
    """
    # 检查权限
    if not deps.check_permissions("user", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 使用用户服务创建用户
    user = user_service.create_user(db, user_in=user_in)
    
    return user


@router.get("/members", response_model=List[schemas.UserMember], summary="员工通讯录最小集")
def read_user_members(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 1000,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    员工通讯录 (最小字段集)

    供家访登记、工作流审批人选择等业务选择器使用 —— 这些流程需要"挑一个人",
    但不需要组织架构与权限信息。刻意不返回 department / roles / is_superuser,
    避免业务下拉框成为全行组织架构和管理员名单的泄露面。

    team_id 是例外, 有意保留: 家访登记用它把"被家访人"下拉限定在本团队,
    而不是列出全行 1494 人。团队归属是员工自己能看到的公开信息。

    注意: 本端点必须声明在下方 `@router.get("/{user_id}")` 之前,
    否则 "members" 会被当成 int 类型的 user_id 而 422。
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=schemas.User)
def read_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取用户详情
    """
    # 检查权限
    if not deps.check_permissions("user", "view", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户角色
    user.roles = get_roles_for_user(str(user.id))
    
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新用户信息
    """
    # 检查权限
    if not deps.check_permissions("user", "edit", current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="没有足够的权限")

    # Phase 0 (评审 P0-3): 无 user:edit 权限的自助更新走白名单 schema。
    # UserUpdate 继承了 is_superuser/is_active/team_id 并带 password/roles,
    # 之前任意登录用户 PUT /users/{自己的id} {"is_superuser": true} 即可自我提权。
    if not deps.check_permissions("user", "edit", current_user):
        user_in = schemas.UserSelfUpdate(**user_in.dict(exclude_unset=True))

    # 使用用户服务更新用户
    # operator_user_id 供 G7 组员调换历史记录操作人 (PRD §11.4)
    return user_service.update_user(
        db, user_id=user_id, user_in=user_in, operator_user_id=current_user.id
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    删除用户
    """
    # 检查权限
    if not deps.check_permissions("user", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    # 使用用户服务删除用户
    user_service.delete_user(db, user_id=user_id)


@router.post("/import", response_model=Dict[str, Any])
def import_users(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
) -> Any:
    """
    批量导入用户
    """
    # 检查权限
    if not deps.check_permissions("user", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查文件类型
    if file.content_type not in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
    ]:
        raise HTTPException(status_code=400, detail="只支持Excel或CSV文件")
    
    try:
        # 读取文件内容
        contents = file.file.read()
        buffer = io.BytesIO(contents)
        
        # 根据文件类型读取数据
        if file.content_type == "text/csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)
        
        # 验证必要的列 (决策 2: 4 列必填, 中文表头为主, 兼容英文别名)
        cols = _resolve_user_import_columns(df)

        # 处理导入结果
        success_count = 0
        failed_users = []

        # 处理每一行数据
        for index, row in df.iterrows():
            # Excel 行号从 2 开始 (第 1 行是表头), 供管理员回到表里定位
            excel_row = index + 2
            name_hint = str(row[cols["name"]]) if pd.notna(row[cols["name"]]) else "未知"
            try:
                # PRD §3.2 + §17.3: 批量导入统一校验 EHR 格式 (恰好 7 位数字)
                ehr_value = str(row[cols["ehr_id"]]).strip()
                if ehr_value.endswith(".0"):  # Excel 把 7 位 EHR 读成数字时会带 .0
                    ehr_value = ehr_value[:-2]
                try:
                    validate_ehr_format(ehr_value)
                except ValueError as e:
                    failed_users.append({
                        "row": excel_row,
                        "username": name_hint,
                        "reason": f"EHR号格式错误: {e}",
                    })
                    continue

                name_value = str(row[cols["name"]]).strip()

                # 决策 2: 初始密码强度校验, 不合规整行失败 (不静默降级成弱密码)
                password_value = row[cols["password"]]
                if pd.isna(password_value):
                    failed_users.append({
                        "row": excel_row,
                        "username": name_hint,
                        "reason": "初始密码为空",
                    })
                    continue
                try:
                    validate_password_strength(str(password_value), label="初始密码")
                except ValueError as e:
                    failed_users.append({
                        "row": excel_row,
                        "username": name_hint,
                        "reason": str(e),
                    })
                    continue

                # 组别按名字匹配。匹配不到整行失败 —— 不静默留空, 否则员工成了
                # 无组孤儿, 后续权限判定 (本项目按组判组长) 会把他当普通员工,
                # 错得没有任何提示。
                team_name_value = str(row[cols["team_name"]]).strip()
                team = (
                    db.query(models.Team)
                    .filter(models.Team.name == team_name_value)
                    .first()
                )
                if not team:
                    failed_users.append({
                        "row": excel_row,
                        "username": name_hint,
                        "reason": f"组别不存在: {team_name_value} (请先在团队管理里建组)",
                    })
                    continue

                # EHR 号是登录标识 (auth.py:25), 唯一; 已存在即整行失败并说明原因
                user_by_ehr_id = db.query(models.User).filter(
                    models.User.ehr_id == ehr_value
                ).first()
                if user_by_ehr_id:
                    failed_users.append({
                        "row": excel_row,
                        "username": name_hint,
                        "reason": f"EHR号已存在 ({user_by_ehr_id.name})",
                    })
                    continue

                # 创建用户
                user = models.User(
                    # username 列 NOT NULL+unique 但不参与登录 (登录走 ehr_id),
                    # 模板不设该列, 用 EHR 号填充保证唯一且可追溯
                    username=ehr_value,
                    ehr_id=ehr_value,
                    hashed_password=get_password_hash(str(password_value)),
                    name=name_value,
                    department="",
                    is_active=True,
                    is_superuser=False,
                    team_id=team.id,
                    last_password_change=datetime.now(),
                )

                db.add(user)
                db.commit()
                db.refresh(user)

                # 决策 2 未定义角色列 —— 统一按普通用户建, 组长身份走
                # teams.leader_id (决策 1), 不在这里靠 casbin 角色表达
                add_role_for_user(str(user.id), "user")

                success_count += 1

            except Exception as e:
                failed_users.append({
                    "row": excel_row,
                    "username": name_hint,
                    "reason": str(e),
                })
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_users),
            "failed_users": failed_users
        }
    
    except HTTPException:
        # 上层已显性化的 4xx (如缺列) 必须原样抛出去, 不能被下面的
        # except Exception 吞成 500 —— 否则管理员看到的是"服务器错误",
        # 完全不知道是自己 Excel 少了一列。
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"导入用户时发生错误: {str(e)}"
        )
    finally:
        file.file.close()


@router.get("/me/permissions", response_model=List[str])
def read_user_permissions(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的权限列表
    """
    # 如果是超级管理员，拥有所有权限
    if current_user.is_superuser:
        return ["*:*"]
    
    # 获取用户角色
    roles = get_roles_for_user(str(current_user.id))
    
    # 获取所有角色的权限
    permissions = []
    for role in roles:
        role_permissions = get_permissions_for_role(role)
        for p in role_permissions:
            # p格式为 [role, resource, action]
            if len(p) >= 3:
                permission = f"{p[1]}:{p[2]}"
                if permission not in permissions:
                    permissions.append(permission)
    
    return permissions 