from typing import Any, List, Optional, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from datetime import datetime
from urllib.parse import quote
from app import models, schemas, crud
from app.utils.logger import LoggerService
from app.schemas.workflow import WorkflowInstanceCreate


class LedgerService:
    """台账服务类"""

    @staticmethod
    def get_ledgers(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        team_id: Optional[int] = None,
        template_id: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        approval_status: Optional[str] = None,
        current_user: models.User = None,
    ) -> List[schemas.Ledger]:
        """
        获取台账列表
        """
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
        
        # 搜索
        if search:
            query = query.filter(models.Ledger.name.ilike(f"%{search}%"))
        
        # 非超级管理员只能看到自己团队的台账
        if current_user and not current_user.is_superuser and not team_id:
            query = query.filter(models.Ledger.team_id == current_user.team_id)
        
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

                # 获取工作流名称
                if template.workflow_id:
                    workflow = db.query(models.Workflow).filter(models.Workflow.id == template.workflow_id).first()
                    if workflow:
                        ledger.workflow_name = workflow.name
        
            
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
            
        return ledgers

    @staticmethod
    def create_ledger(
        db: Session,
        ledger_in: schemas.LedgerCreate,
        current_user: models.User
    ) -> schemas.Ledger:
        """
        创建新台账
        """
        # 检查模板是否存在
        template = None
        if ledger_in.template_id:
            template = db.query(models.Template).filter(models.Template.id == ledger_in.template_id).first()
            if not template:
                raise HTTPException(status_code=404, detail="模板不存在")
        
        # 从模板获取默认值
        description = ledger_in.description
        status = ledger_in.status or "draft"
        
        if template:
                
            if not description and template.default_description:
                description = template.default_description
                
            workflow_id = template.workflow_id
        
        # 确保必须的值存在
        if not ledger_in.name:
            raise HTTPException(status_code=400, detail="台账名称不能为空")
        
        # 检查团队是否存在
        if ledger_in.team_id:
            team = db.query(models.Team).filter(models.Team.id == ledger_in.team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="团队不存在")
        
        # 检查工作流是否存在
        if workflow_id:
            workflow = db.query(models.Workflow).filter(
                models.Workflow.id == workflow_id,
                models.Workflow.is_active == True
            ).first()
            if not workflow:
                raise HTTPException(status_code=404, detail="工作流不存在或未激活")
        
        # 创建台账
        ledger = crud.ledger.create(
            db, 
            obj_in=ledger_in,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        # 如果台账中包含data数据，同步创建字段值
        if ledger.data and template:
            LedgerService.sync_field_values_with_ledger_data(db, ledger.id)
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="create",
            message=f"创建台账 {ledger.name}",
            user_id=current_user.id,
            resource_type="ledger",
            resource_id=str(ledger.id)
        )
        
        return ledger

    @staticmethod
    def get_ledger(
        db: Session,
        ledger_id: int,
        current_user: models.User
    ) -> schemas.Ledger:
        """
        获取指定台账详情
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 非超级管理员只能查看自己团队的台账
        if not current_user.is_superuser and ledger.team_id != current_user.team_id:
            # 检查用户是否是创建者
            if ledger.created_by_id != current_user.id:
                # 检查用户是否是审批人
                if ledger.workflow_instance_id:
                    # 检查用户是否在审批节点中
                    workflow_instance = db.query(models.WorkflowInstance).filter(
                        models.WorkflowInstance.id == ledger.workflow_instance_id
                    ).first()
                    
                    if workflow_instance and workflow_instance.current_node_id:
                        current_node = db.query(models.WorkflowInstanceNode).filter(
                            models.WorkflowInstanceNode.id == workflow_instance.current_node_id
                        ).first()
                        
                        if current_node and current_node.approver_id != current_user.id:
                            raise HTTPException(status_code=403, detail="无权查看此台账")
                else:
                    raise HTTPException(status_code=403, detail="无权查看此台账")
        
        # 获取台账的相关数据（团队名称、模板名称等）
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
        
            # 获取工作流名称
            if template.workflow_id:
                workflow = db.query(models.Workflow).filter(models.Workflow.id == template.workflow_id).first()
                if workflow:
                    ledger.workflow_name = workflow.name
        
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
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="view",
            message=f"查看台账 {ledger.name}",
            user_id=current_user.id,
            resource_type="ledger",
            resource_id=str(ledger.id)
        )
        
        return ledger

    @staticmethod
    def update_ledger(
        db: Session,
        ledger_id: int,
        ledger_in: schemas.LedgerUpdate,
        current_user: models.User
    ) -> schemas.Ledger:
        """
        更新台账
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 检查是否可以编辑
        if ledger.status not in ["draft", "returned"]:
            raise HTTPException(status_code=400, detail="只能编辑草稿或退回状态的台账")
        
        # 非超级管理员只能更新自己创建的台账或自己团队的台账
        if not current_user.is_superuser:
            if ledger.created_by_id != current_user.id and ledger.team_id != current_user.team_id:
                raise HTTPException(status_code=403, detail="无权更新此台账")
        
        # 更新台账信息
        update_data = ledger_in.dict(exclude_unset=True)
        
        # 检查团队是否存在
        if "team_id" in update_data and update_data["team_id"]:
            team = db.query(models.Team).filter(models.Team.id == update_data["team_id"]).first()
            if not team:
                raise HTTPException(status_code=404, detail="团队不存在")
        
        # 检查模板是否存在
        if "template_id" in update_data and update_data["template_id"]:
            template = db.query(models.Template).filter(models.Template.id == update_data["template_id"]).first()
            if not template:
                raise HTTPException(status_code=404, detail="模板不存在")
        
        # 标记数据变更
        data_changed = "data" in update_data and update_data["data"] != ledger.data
            
        # 更新台账
        ledger = crud.ledger.update(
            db, 
            db_obj=ledger,
            obj_in=update_data,
            updated_by_id=current_user.id
        )
        
        # 如果data字段有变更且模板存在，同步更新字段值
        if data_changed and ledger.template_id:
            LedgerService.sync_field_values_with_ledger_data(db, ledger.id)
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="update",
            message=f"更新台账 {ledger.name}",
            user_id=current_user.id,
            resource_type="ledger",
            resource_id=str(ledger.id)
        )
        
        return ledger

    @staticmethod
    def delete_ledger(
        db: Session,
        ledger_id: int,
        current_user: models.User
    ) -> schemas.Ledger:
        """
        删除台账
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 非超级管理员只能删除自己创建的台账
        if not current_user.is_superuser and ledger.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此台账")
        
        # 检查是否可以删除
        if ledger.status not in ["draft"]:
            raise HTTPException(status_code=400, detail="只能删除草稿状态的台账")
        
        # 记录日志
        ledger_name = ledger.name
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="delete",
            message=f"删除台账 {ledger_name}",
            user_id=current_user.id,
            resource_type="ledger",
            resource_id=str(ledger.id)
        )
        
        # 删除台账
        db.delete(ledger)
        db.commit()
        
        return ledger

    @staticmethod
    def export_ledger(
        db: Session,
        ledger_id: int,
        format: str,
        current_user: models.User
    ) -> tuple:
        """
        导出台账
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 非超级管理员只能导出自己团队的台账
        if not current_user.is_superuser and ledger.team_id != current_user.team_id:
            # 检查用户是否是创建者
            if ledger.created_by_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权导出此台账")
        
        # 准备数据
        data = {
            "ID": [ledger.id],
            "名称": [ledger.name],
            "描述": [ledger.description or ""],
            "状态": [ledger.status],
            "审批状态": [ledger.approval_status],
            "创建时间": [ledger.created_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.created_at else ""],
            "更新时间": [ledger.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.updated_at else ""],
        }
        
        # 添加模板字段数据
        if ledger.template_id and ledger.data:
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
            if template:
                # 获取模板字段
                fields = db.query(models.Field).filter(
                    models.Field.template_id == template.id
                ).all()
                
                for field in fields:
                    key = field.name
                    value = ledger.data.get(field.name, "")
                    data[key] = [value]
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 导出文件
        file_data = BytesIO()
        
        if format.lower() == "excel":
            df.to_excel(file_data, index=False)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{ledger.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        elif format.lower() == "csv":
            df.to_csv(file_data, index=False)
            content_type = "text/csv"
            filename = f"{ledger.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        else:  # txt
            df.to_csv(file_data, index=False, sep="\t")
            content_type = "text/plain"
            filename = f"{ledger.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        
        file_data.seek(0)
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="export",
            message=f"导出台账 {ledger.name}",
            user_id=current_user.id,
            resource_type="ledger",
            resource_id=str(ledger.id)
        )
        
        return file_data, filename, content_type

    @staticmethod
    def export_all_ledgers(
        db: Session,
        format: str,
        template_id: Optional[int] = None,
        current_user: models.User = None
    ) -> tuple:
        """
        导出所有台账
        """
        # 构建查询
        query = db.query(models.Ledger)
        
        # 按模板筛选
        if template_id:
            query = query.filter(models.Ledger.template_id == template_id)
        
        # 非超级管理员只能看到自己团队的台账
        if current_user and not current_user.is_superuser:
            query = query.filter(models.Ledger.team_id == current_user.team_id)
        
        # 获取台账列表
        ledgers = query.all()
        
        # 准备数据
        data = {
            "ID": [],
            "名称": [],
            "描述": [],
            "状态": [],
            "审批状态": [],
            "创建时间": [],
            "更新时间": [],
        }
        
        # 添加台账数据
        for ledger in ledgers:
            data["ID"].append(ledger.id)
            data["名称"].append(ledger.name)
            data["描述"].append(ledger.description or "")
            data["状态"].append(ledger.status)
            data["审批状态"].append(ledger.approval_status)
            data["创建时间"].append(ledger.created_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.created_at else "")
            data["更新时间"].append(ledger.updated_at.strftime("%Y-%m-%d %H:%M:%S") if ledger.updated_at else "")
        
        # 如果有模板，添加模板字段列
        if template_id:
            template = db.query(models.Template).filter(models.Template.id == template_id).first()
            if template:
                # 获取模板字段
                fields = db.query(models.Field).filter(
                    models.Field.template_id == template.id
                ).all()
                
                for field in fields:
                    key = field.name
                    data[key] = []
                    
                    for ledger in ledgers:
                        if ledger.data and field.name in ledger.data:
                            data[key].append(ledger.data[field.name])
                        else:
                            data[key].append("")
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 导出文件
        file_data = BytesIO()
        
        template_name = ""
        if template_id:
            template = db.query(models.Template).filter(models.Template.id == template_id).first()
            if template:
                template_name = f"_{template.name}"
        
        if format.lower() == "excel":
            df.to_excel(file_data, index=False)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"台账列表{template_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        elif format.lower() == "csv":
            df.to_csv(file_data, index=False)
            content_type = "text/csv"
            filename = f"台账列表{template_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        else:  # txt
            df.to_csv(file_data, index=False, sep="\t")
            content_type = "text/plain"
            filename = f"台账列表{template_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        
        file_data.seek(0)
        
        # 记录日志
        LoggerService.log_info(
            db=db,
            module="ledger",
            action="export_all",
            message=f"导出所有台账列表",
            user_id=current_user.id if current_user else None,
        )
        
        return file_data, filename, content_type

    @staticmethod
    def sync_ledger_data_with_field_values(db: Session, ledger_id: int) -> Dict:
        """
        同步台账的data字段和field_values表
        将field_values表中的数据同步到ledger的data字段中
        
        返回同步后的data字典
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 获取字段值
        field_values = crud.field_value.get_by_ledger(db, ledger_id=ledger_id)
        
        # 初始化data字典
        data = {}
        if ledger.data:
            data = ledger.data
        
        # 获取模板字段信息，以便获取字段名称
        template = None
        if ledger.template_id:
            template = db.query(models.Template).filter(models.Template.id == ledger.template_id).first()
        
        # 更新data字典
        for field_value in field_values:
            # 获取字段信息
            field = db.query(models.Field).filter(models.Field.id == field_value.field_id).first()
            if field:
                # 使用字段名称作为键
                data[field.name] = field_value.value
        
        # 更新台账的data字段
        ledger.data = data
        db.add(ledger)
        db.commit()
        db.refresh(ledger)
        
        return data
        
        
    @staticmethod
    def sync_field_values_with_ledger_data(db: Session, ledger_id: int) -> List[models.FieldValue]:
        """
        同步field_values表和台账的data字段
        将ledger的data字段中的数据同步到field_values表中
        
        返回同步后的字段值列表
        """
        # 获取台账
        ledger = db.query(models.Ledger).filter(models.Ledger.id == ledger_id).first()
        if not ledger:
            raise HTTPException(status_code=404, detail="台账不存在")
        
        # 如果没有data或模板ID，则返回空列表
        if not ledger.data or not ledger.template_id:
            return []
        
        # 获取模板的所有字段
        fields = db.query(models.Field).filter(models.Field.template_id == ledger.template_id).all()
        
        # 获取当前的字段值
        current_field_values = crud.field_value.get_by_ledger(db, ledger_id=ledger_id)
        current_field_values_dict = {fv.field_id: fv for fv in current_field_values}
        
        # 字段值列表
        result_field_values = []
        
        # 遍历模板字段
        for field in fields:
            # 检查data中是否有对应的值
            if field.name in ledger.data:
                # 将所有值转换为字符串
                value = ledger.data[field.name]
                if value is not None:  # 确保值不为None
                    value = str(value)  # 将所有类型转换为字符串
                
                # 如果已存在字段值，则更新
                if field.id in current_field_values_dict:
                    field_value = current_field_values_dict[field.id]
                    field_value.value = value
                    db.add(field_value)
                    result_field_values.append(field_value)
                else:
                    # 如果不存在，则创建新的字段值
                    field_value_in = schemas.FieldValueCreate(
                        field_id=field.id,
                        value=value
                    )
                    field_value = crud.field_value.create(db, obj_in=field_value_in, ledger_id=ledger_id)
                    result_field_values.append(field_value)
        
        db.commit()
        
        return result_field_values


ledger_service = LedgerService() 