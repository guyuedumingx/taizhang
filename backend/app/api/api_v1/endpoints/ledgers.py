from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Ledger])
def read_ledgers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = None,
    template_id: Optional[int] = None,
    search: Optional[str] = None,
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
    
    # 搜索
    if search:
        query = query.filter(models.Ledger.name.ilike(f"%{search}%"))
    
    # 非超级管理员只能看到自己团队的台账
    if not current_user.is_superuser and not team_id:
        query = query.filter(models.Ledger.team_id == current_user.team_id)
    
    # 获取总数
    total = query.count()
    
    # 分页
    ledgers = query.offset(skip).limit(limit).all()
    
    # 获取关联信息
    for ledger in ledgers:
        # 获取创建者和更新者信息
        if ledger.created_by_id:
            creator = db.query(models.User).filter(models.User.id == ledger.created_by_id).first()
            ledger.created_by_name = creator.name if creator else None
        
        if ledger.updated_by_id:
            updater = db.query(models.User).filter(models.User.id == ledger.updated_by_id).first()
            ledger.updated_by_name = updater.name if updater else None
        
        # 获取团队信息
        if ledger.team_id:
            team = db.query(models.Team).filter(models.Team.id == ledger.team_id).first()
            ledger.team_name = team.name if team else None
        
        # 获取模板信息
        if ledger.template_id:
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
            ledger.template_name = template.name if template else None
    
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
    
    # 检查团队是否存在
    if ledger_in.team_id:
        team = db.query(models.Team).filter(models.Team.id == ledger_in.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
    
    # 检查模板是否存在
    if ledger_in.template_id:
        template = db.query(models.Template).filter(models.Template.id == ledger_in.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
    
    # 创建台账
    ledger = models.Ledger(
        name=ledger_in.name,
        description=ledger_in.description,
        team_id=ledger_in.team_id or current_user.team_id,
        template_id=ledger_in.template_id,
        data=ledger_in.data or {},
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    
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