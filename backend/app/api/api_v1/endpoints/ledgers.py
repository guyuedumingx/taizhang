from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Response
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from datetime import datetime
from urllib.parse import quote

from app import models, schemas, crud
from app.api import deps
from app.utils.logger import LoggerService

router = APIRouter()


@router.get("/", response_model=List[schemas.Ledger])
def read_ledgers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = None,
    template_id: Optional[int] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    workflow_id: Optional[int] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账列表
    """
    # 检查权限
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 构建查询
    query = db.query(models.Ledger)
    
    # 按团队筛选
    if team_id:
        query = query.filter(models.Ledger.team_id == team_id)
    
    # 按模板筛选
    if template_id:
        query = query.filter(models.Ledger.template_id == template_id)
    
    # 按状态筛选
    if status:
        query = query.filter(models.Ledger.status == status)
    
    # 按审批状态筛选
    if approval_status:
        query = query.filter(models.Ledger.approval_status == approval_status)
    
    # 按工作流筛选
    if workflow_id:
        query = query.filter(models.Ledger.workflow_id == workflow_id)
    
    # 搜索
    if search:
        query = query.filter(models.Ledger.name.ilike(f"%{search}%"))
    
    # 非超级管理员只能看到自己团队的台账
    if not current_user.is_superuser and not team_id:
        query = query.filter(models.Ledger.team_id == current_user.team_id)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="list",
        message="查询台账列表",
        user_id=current_user.id,
    )
    
    # 获取台账列表
    ledgers = query.order_by(models.Ledger.updated_at.desc()).offset(skip).limit(limit).all()
    
    # 获取台账的相关数据（团队名称、模板名称等）
    for ledger in ledgers:
        # 获取团队名称
        if ledger.team_id:
            team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
            if team:
                ledger.team_name = team.name
        
        # 获取模板名称
        if ledger.template_id:
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
            if template:
                ledger.template_name = template.name
        
        # 获取创建人和更新人姓名
        creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
        if creator:
            ledger.created_by_name = creator.name
        
        updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
        if updater:
            ledger.updated_by_name = updater.name
        
        # 获取当前审批人姓名
        if ledger.current_approver_id:
            approver = db.query(models.User).filter(models.User.id == ledger.current_approver_id).first()
            if approver:
                ledger.current_approver_name = approver.name
        
        # 获取工作流名称
        if ledger.workflow_id:
            workflow = db.query(models.Workflow).filter(models.Workflow.id == ledger.workflow_id).first()
            if workflow:
                ledger.workflow_name = workflow.name
    
    return ledgers


@router.post("/", response_model=schemas.Ledger)
def create_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_in: schemas.LedgerCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "create", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 检查模板是否存在
    template = None
    if ledger_in.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger_in.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
    
    # 从模板获取默认值
    name = ledger_in.name
    description = ledger_in.description
    team_id = ledger_in.team_id or current_user.team_id
    status = ledger_in.status or "draft"
    
    if template:
        # 如果未提供值，则使用模板默认值
        if not name and template.default_ledger_name:
            name = template.default_ledger_name
            
        if not description and template.default_description:
            description = template.default_description
            
        if not ledger_in.team_id and template.default_team_id:
            team_id = template.default_team_id
            
        if not ledger_in.status and template.default_status:
            status = template.default_status
    
    # 确保必须的值存在
    if not name:
        raise HTTPException(status_code=400, detail="台账名称不能为空")
    
    # 检查团队是否存在
    if team_id:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
    
    # 检查工作流是否存在
    workflow_id = ledger_in.workflow_id
    if workflow_id:
        workflow = db.query(models.Workflow).filter(
            models.Workflow.id == workflow_id,
            models.Workflow.is_active == True
        ).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在或未激活")
    
    # 创建台账
    ledger = models.Ledger(
        name=name,
        description=description,
        team_id=team_id,
        template_id=ledger_in.template_id,
        workflow_id=workflow_id,
        data=ledger_in.data or {},
        status=status,
        approval_status="pending",
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="create",
        message=f"创建台账 {ledger.name}",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id),
    )
    
    # 获取关联信息
    if ledger.created_by_id:
        creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
        ledger.created_by_name = creator.name if creator else None
    
    if ledger.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
        ledger.updated_by_name = updater.name if updater else None
    
    if ledger.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
        ledger.team_name = team.name if team else None
    
    if ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        ledger.template_name = template.name if template else None
    
    if ledger.workflow_id:
        workflow = db.query(models.Workflow).filter(models.Workflow.id == ledger.workflow_id).first()
        ledger.workflow_name = workflow.name if workflow else None
    
    return ledger


@router.get("/{ledger_id}", response_model=schemas.Ledger)
def read_ledger(
    ledger_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取台账详情
    """
    # 检查权限
    if not deps.check_permissions("ledger", "view", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能看到自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="没有权限查看其他团队的台账")
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="read",
        message=f"查看台账 {ledger.name}",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id),
    )
    
    # 获取关联信息
    if ledger.created_by_id:
        creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
        ledger.created_by_name = creator.name if creator else None
    
    if ledger.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
        ledger.updated_by_name = updater.name if updater else None
    
    if ledger.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
        ledger.team_name = team.name if team else None
    
    if ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        ledger.template_name = template.name if template else None
    
    # 获取当前审批人姓名
    if ledger.current_approver_id:
        approver = db.query(models.User).filter(models.User.id == ledger.current_approver_id).first()
        if approver:
            ledger.current_approver_name = approver.name
    
    # 获取工作流名称
    if ledger.workflow_id:
        workflow = db.query(models.Workflow).filter(models.Workflow.id == ledger.workflow_id).first()
        if workflow:
            ledger.workflow_name = workflow.name
    
    # 获取活动的工作流实例
    if ledger.status == "active" and ledger.approval_status == "pending":
        workflow_instance = crud.workflow_instance.get_active_by_ledger(db, ledger_id=ledger_id)
        if workflow_instance:
            # 获取工作流实例节点
            workflow_instance.nodes = crud.workflow_instance_node.get_by_instance(
                db, instance_id=workflow_instance.id
            )
            ledger.active_workflow_instance = workflow_instance
    
    return ledger


@router.put("/{ledger_id}", response_model=schemas.Ledger)
def update_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int,
    ledger_in: schemas.LedgerUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新台账信息
    """
    # 检查权限
    if not deps.check_permissions("ledger", "edit", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能更新自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="没有权限更新其他团队的台账")
    
    # 检查台账状态，如果不是草稿状态且不是管理员，则不能更新
    if ledger.status != "draft" and not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="只有草稿状态的台账可以更新")
    
    # 检查团队是否存在
    if ledger_in.team_id and ledger_in.team_id != ledger.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger_in.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
    
    # 检查模板是否存在
    if ledger_in.template_id and ledger_in.template_id != ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger_in.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
    
    # 检查工作流是否存在
    if ledger_in.workflow_id and ledger_in.workflow_id != ledger.workflow_id:
        workflow = db.query(models.Workflow).filter(
            models.Workflow.id == ledger_in.workflow_id,
            models.Workflow.is_active == True
        ).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="工作流不存在或未激活")
    
    # 更新台账信息
    update_data = ledger_in.dict(exclude_unset=True)
    
    # 处理数据更新
    if "data" in update_data:
        # 合并数据而不是替换
        current_data = ledger.data or {}
        new_data = update_data["data"] or {}
        merged_data = {**current_data, **new_data}
        update_data["data"] = merged_data
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(ledger, field, value)
    
    # 更新更新者和更新时间
    ledger.updated_by_id = current_user.id
    
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    
    # 记录日志
    LoggerService.log_info(
        db=db,
        module="ledger",
        action="update",
        message=f"更新台账 {ledger.name}",
        user_id=current_user.id,
        resource_type="ledger",
        resource_id=str(ledger.id),
    )
    
    # 获取关联信息
    if ledger.created_by_id:
        creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
        ledger.created_by_name = creator.name if creator else None
    
    if ledger.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
        ledger.updated_by_name = updater.name if updater else None
    
    if ledger.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
        ledger.team_name = team.name if team else None
    
    if ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        ledger.template_name = template.name if template else None
    
    if ledger.current_approver_id:
        approver = db.query(models.User).filter(models.User.id == ledger.current_approver_id).first()
        if approver:
            ledger.current_approver_name = approver.name
    
    if ledger.workflow_id:
        workflow = db.query(models.Workflow).filter(models.Workflow.id == ledger.workflow_id).first()
        if workflow:
            ledger.workflow_name = workflow.name
    
    return ledger


@router.delete("/{ledger_id}", response_model=schemas.Ledger)
def delete_ledger(
    *,
    db: Session = Depends(deps.get_db),
    ledger_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除台账
    """
    # 检查权限
    if not deps.check_permissions("ledger", "delete", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 非超级管理员只能删除自己团队的台账
    if not current_user.is_superuser and ledger.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="没有权限删除其他团队的台账")
    
    # 获取关联信息用于返回
    if ledger.created_by_id:
        creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
        ledger.created_by_name = creator.name if creator else None
    
    if ledger.updated_by_id:
        updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
        ledger.updated_by_name = updater.name if updater else None
    
    if ledger.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
        ledger.team_name = team.name if team else None
    
    if ledger.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        ledger.template_name = template.name if template else None
    
    # 删除台账
    db.delete(ledger)
    db.commit()
    
    return ledger


@router.get("/{ledger_id}/export", response_class=Response)
def export_ledger(
    *,
    ledger_id: int = Path(...),
    format: str = Query(..., description="导出格式，支持excel、csv、txt"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出台账数据
    """
    # 检查权限
    if not deps.check_permissions("ledger", "export", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    # 获取台账
    ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    
    # 获取台账字段
    template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 只获取关键字段
    fields = db.query(models.Field).filter(
        models.Field.template_id == template.id,
        models.Field.is_key_field == True
    ).all()
    
    # 准备数据
    data = {
        "台账ID": ledger.id,
        "标题": ledger.name,
        "描述": ledger.description,
        "创建时间": ledger.created_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.created_at else "",
        "更新时间": ledger.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.updated_at else "",
        "创建人": db.query(models.User).filter(models.User.id == ledger.created_by_id).first().name if ledger.created_by_id else "",
        "更新人": db.query(models.User).filter(models.User.id == ledger.updated_by_id).first().name if ledger.updated_by_id else "",
    }
    
    # 添加自定义字段数据
    for field in fields:
        field_value = db.query(models.FieldValue).filter(
            models.FieldValue.ledger_id == ledger.id,
            models.FieldValue.field_id == field.id
        ).first()
        
        data[field.name] = field_value.value if field_value else ""
    
    # 创建DataFrame
    df = pd.DataFrame([data])
    
    # 根据格式导出
    if format.lower() == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="台账数据")
            # 调整列宽
            worksheet = writer.sheets["台账数据"]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
        
        output.seek(0)
        filename = f"台账_{ledger.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        encoded_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        return Response(
            content=output.getvalue(),
            headers=headers
        )
    
    elif format.lower() == "csv":
        output = BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        filename = f"台账_{ledger.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        encoded_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
        return Response(
            content=output.getvalue(),
            headers=headers
        )
    
    elif format.lower() == "txt":
        output = BytesIO()
        df.to_csv(output, index=False, sep="\t", encoding="utf-8")
        output.seek(0)
        filename = f"台账_{ledger.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        encoded_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Type": "text/plain; charset=utf-8"
        }
        return Response(
            content=output.getvalue(),
            headers=headers
        )
    
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式，支持的格式：excel、csv、txt")


@router.get("/export-all", response_class=Response)
def export_all_ledgers(
    *,
    format: str = Query(..., description="导出格式，支持excel、csv、txt"),
    template_id: Optional[int] = Query(None, description="模板ID，用于筛选特定模板的台账"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出所有台账数据
    """
    # 打印请求参数
    print(f"导出所有台账 - 格式: {format}, 模板ID: {template_id}")
    
    # 验证格式参数
    if format.lower() not in ["excel", "csv", "txt"]:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}，支持的格式：excel、csv、txt")
    
    # 验证模板ID
    if template_id is not None:
        if not isinstance(template_id, int):
            raise HTTPException(status_code=422, detail=f"模板ID必须是整数，收到的类型: {type(template_id)}")
        
        # 检查模板是否存在
        template = db.query(models.Template).filter(models.Template.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail=f"未找到ID为{template_id}的模板")
    
    # 检查权限
    if not deps.check_permissions("ledger", "export", current_user):
        raise HTTPException(status_code=403, detail="没有足够的权限")
    
    try:
        # 获取台账列表
        query = db.query(models.Ledger)
        if template_id:
            query = query.filter(models.Ledger.template_id == template_id)
        
        ledgers = query.all()
        if not ledgers:
            raise HTTPException(status_code=404, detail="没有找到符合条件的台账")
        
        # 准备数据
        all_data = []
        
        for ledger in ledgers:
            # 获取台账字段
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
            if not template:
                continue
            
            # 只获取关键字段
            fields = db.query(models.Field).filter(
                models.Field.template_id == template.id,
                models.Field.is_key_field == True
            ).all()
            
            data = {
                "台账ID": ledger.id,
                "标题": ledger.name,
                "描述": ledger.description,
                "模板": template.name,
                "创建时间": ledger.created_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.created_at else "",
                "更新时间": ledger.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.updated_at else "",
                "创建人": db.query(models.User).filter(models.User.id == ledger.created_by_id).first().name if ledger.created_by_id else "",
                "更新人": db.query(models.User).filter(models.User.id == ledger.updated_by_id).first().name if ledger.updated_by_id else "",
            }
            
            # 添加自定义字段数据
            for field in fields:
                field_value = db.query(models.FieldValue).filter(
                    models.FieldValue.ledger_id == ledger.id,
                    models.FieldValue.field_id == field.id
                ).first()
                
                data[f"{template.name}_{field.name}"] = field_value.value if field_value else ""
            
            all_data.append(data)
        
        # 创建DataFrame
        df = pd.DataFrame(all_data)
        
        # 根据格式导出
        if format.lower() == "excel":
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="台账数据")
                # 调整列宽
                worksheet = writer.sheets["台账数据"]
                for i, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)
            
            output.seek(0)
            filename = f"台账列表_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            encoded_filename = quote(filename)
            headers = {
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
            return Response(
                content=output.getvalue(),
                headers=headers
            )
        
        elif format.lower() == "csv":
            output = BytesIO()
            df.to_csv(output, index=False, encoding="utf-8-sig")
            output.seek(0)
            filename = f"台账列表_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            encoded_filename = quote(filename)
            headers = {
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
            return Response(
                content=output.getvalue(),
                headers=headers
            )
        
        elif format.lower() == "txt":
            output = BytesIO()
            df.to_csv(output, index=False, sep="\t", encoding="utf-8")
            output.seek(0)
            filename = f"台账列表_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
            encoded_filename = quote(filename)
            headers = {
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Content-Type": "text/plain; charset=utf-8"
            }
            return Response(
                content=output.getvalue(),
                headers=headers
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式，支持的格式：excel、csv、txt")
    
    except Exception as e:
        LoggerService.log_error(
            db=db,
            module="ledger",
            action="export-all",
            message=f"导出所有台账数据时发生错误: {str(e)}",
            user_id=current_user.id,
        )
        raise HTTPException(status_code=500, detail="导出所有台账数据时发生错误") 