import logging
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import models, crud
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.services.casbin_service import add_role_for_user

logger = logging.getLogger(__name__)


def insert_test_data():
    db = SessionLocal()
    try:
        insert_test_users(db)
        insert_test_teams(db)
        insert_test_templates(db)
        insert_test_workflows(db)
        insert_test_ledgers(db)
        db.commit()
        logger.info("测试数据插入成功")
    except Exception as e:
        db.rollback()
        logger.error(f"插入测试数据失败: {e}")
    finally:
        db.close()


def insert_test_users(db: Session):
    """插入测试用户数据"""
    # 检查用户是否已存在
    users = [
        {
            "username": "manager",
            "ehr_id": "0000002",
            "name": "部门经理",
            "department": "管理部",
            "hashed_password": get_password_hash("manager123"),
            "is_active": True,
            "is_superuser": False,
        },
        {
            "username": "user1",
            "ehr_id": "0000003",
            "name": "普通用户1",
            "department": "财务部",
            "hashed_password": get_password_hash("user123"),
            "is_active": True,
            "is_superuser": False,
        },
        {
            "username": "user2",
            "ehr_id": "0000004",
            "name": "普通用户2",
            "department": "人事部",
            "hashed_password": get_password_hash("user123"),
            "is_active": True,
            "is_superuser": False,
        },
    ]
    
    # 创建测试用户
    for user_data in users:
        username = user_data["username"]
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(**user_data)
            db.add(user)
            db.flush()
            
            # 分配角色
            role_name = "manager" if username == "manager" else "user"
            add_role_for_user(str(user.id), role_name)
            logger.info(f"创建测试用户: {username}")


def insert_test_teams(db: Session):
    """插入测试团队数据"""
    teams = [
        {"name": "管理团队", "description": "公司管理层团队"},
        {"name": "财务团队", "description": "公司财务部门团队"},
        {"name": "人事团队", "description": "公司人事部门团队"},
    ]
    
    for team_data in teams:
        team = db.query(models.Team).filter(models.Team.name == team_data["name"]).first()
        if not team:
            team = models.Team(**team_data)
            db.add(team)
            logger.info(f"创建测试团队: {team_data['name']}")


def insert_test_templates(db: Session):
    """插入测试模板数据"""
    templates = [
        {
            "name": "报销单",
            "description": "员工报销申请单",
            "department": "财务部",
            "is_system": False,
            "require_approval": True,
            "fields": [
                {"name": "报销金额", "description": "报销的总金额", "field_type": "number", "is_required": True, "order_index": 0},
                {"name": "报销类型", "description": "报销的类型", "field_type": "select", "is_required": True, "order_index": 1, "options": ["差旅费", "办公用品", "招待费", "其他"]},
                {"name": "报销事由", "description": "报销的原因", "field_type": "text", "is_required": True, "order_index": 2},
                {"name": "报销凭证", "description": "报销的凭证", "field_type": "file", "is_required": False, "order_index": 3},
            ]
        },
        {
            "name": "请假单",
            "description": "员工请假申请单",
            "department": "人事部",
            "is_system": False,
            "require_approval": True,
            "fields": [
                {"name": "请假类型", "description": "请假的类型", "field_type": "select", "is_required": True, "order_index": 0, "options": ["年假", "病假", "事假", "婚假", "产假", "丧假"]},
                {"name": "开始日期", "description": "请假的开始日期", "field_type": "date", "is_required": True, "order_index": 1},
                {"name": "结束日期", "description": "请假的结束日期", "field_type": "date", "is_required": True, "order_index": 2},
                {"name": "请假天数", "description": "请假的天数", "field_type": "number", "is_required": True, "order_index": 3},
                {"name": "请假原因", "description": "请假的原因", "field_type": "textarea", "is_required": True, "order_index": 4},
            ]
        },
        {
            "name": "工作日报",
            "description": "员工每日工作汇报",
            "department": "所有部门",
            "is_system": False,
            "require_approval": False,
            "fields": [
                {"name": "日期", "description": "工作日期", "field_type": "date", "is_required": True, "order_index": 0},
                {"name": "今日工作内容", "description": "今日完成的工作内容", "field_type": "textarea", "is_required": True, "order_index": 1},
                {"name": "明日工作计划", "description": "明日工作计划", "field_type": "textarea", "is_required": True, "order_index": 2},
                {"name": "工作疑难问题", "description": "工作中遇到的问题", "field_type": "textarea", "is_required": False, "order_index": 3},
            ]
        }
    ]
    
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    
    for template_data in templates:
        template_name = template_data["name"]
        template = db.query(models.Template).filter(models.Template.name == template_name).first()
        if not template:
            fields = template_data.pop("fields")
            template = models.Template(**template_data, created_by_id=admin_user.id, updated_by_id=admin_user.id)
            db.add(template)
            db.flush()
            
            for field_data in fields:
                field = models.Field(**field_data, template_id=template.id)
                db.add(field)
            
            logger.info(f"创建测试模板: {template_name}")


def insert_test_workflows(db: Session):
    """插入测试工作流数据"""
    # 获取角色和用户ID
    manager_role = db.query(models.Role).filter(models.Role.name == "manager").first()
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    manager_user = db.query(models.User).filter(models.User.username == "manager").first()
    
    report_template = db.query(models.Template).filter(models.Template.name == "报销单").first()
    leave_template = db.query(models.Template).filter(models.Template.name == "请假单").first()
    
    workflows = [
        {
            "name": "报销审批流程",
            "description": "报销单审批流程",
            "template_id": report_template.id if report_template else 1,
            "is_active": True,
            "nodes": [
                {
                    "name": "开始",
                    "description": "审批流开始",
                    "node_type": "start",
                    "order_index": 0,
                },
                {
                    "name": "部门经理审批",
                    "description": "部门经理审批节点",
                    "node_type": "approval",
                    "approver_role_id": manager_role.id if manager_role else None,
                    "order_index": 1,
                },
                {
                    "name": "管理员审批",
                    "description": "管理员审批节点",
                    "node_type": "approval",
                    "approver_user_id": admin_user.id if admin_user else None,
                    "order_index": 2,
                },
                {
                    "name": "结束",
                    "description": "审批流结束",
                    "node_type": "end",
                    "order_index": 3,
                    "is_final": True,
                },
            ]
        },
        {
            "name": "请假审批流程",
            "description": "请假单审批流程",
            "template_id": leave_template.id if leave_template else 2,
            "is_active": True,
            "nodes": [
                {
                    "name": "开始",
                    "description": "审批流开始",
                    "node_type": "start",
                    "order_index": 0,
                },
                {
                    "name": "部门经理审批",
                    "description": "部门经理审批",
                    "node_type": "approval",
                    "approver_user_id": manager_user.id if manager_user else None,
                    "order_index": 1,
                },
                {
                    "name": "结束",
                    "description": "审批流结束",
                    "node_type": "end",
                    "order_index": 2,
                    "is_final": True,
                },
            ]
        }
    ]
    
    for workflow_data in workflows:
        workflow_name = workflow_data["name"]
        workflow = db.query(models.Workflow).filter(models.Workflow.name == workflow_name).first()
        if not workflow:
            nodes = workflow_data.pop("nodes")
            workflow = models.Workflow(**workflow_data)
            db.add(workflow)
            db.flush()
            
            for node_data in nodes:
                node = models.WorkflowNode(**node_data, workflow_id=workflow.id)
                db.add(node)
            
            logger.info(f"创建测试工作流: {workflow_name}")


def insert_test_ledgers(db: Session):
    """插入测试台账数据"""
    # 获取用户
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    user1 = db.query(models.User).filter(models.User.username == "user1").first()
    user2 = db.query(models.User).filter(models.User.username == "user2").first()
    
    # 获取模板
    report_template = db.query(models.Template).filter(models.Template.name == "报销单").first()
    leave_template = db.query(models.Template).filter(models.Template.name == "请假单").first()
    daily_template = db.query(models.Template).filter(models.Template.name == "工作日报").first()
    
    # 获取工作流
    report_workflow = db.query(models.Workflow).filter(models.Workflow.name == "报销审批流程").first()
    leave_workflow = db.query(models.Workflow).filter(models.Workflow.name == "请假审批流程").first()
    
    ledgers = [
        # 已提交待审批的报销单
        {
            "name": "差旅费报销",
            "description": "出差上海报销费用",
            "template_id": report_template.id if report_template else 1,
            "created_by_id": user1.id if user1 else 1,
            "data": {
                "报销金额": 5000,
                "报销类型": "差旅费",
                "报销事由": "参加上海展会",
                "报销凭证": "receipt.jpg"
            },
            "status": "submitted",
            "submitted": True,
            "workflow_id": report_workflow.id if report_workflow else 1,
            "current_node_id": 2  # 部门经理审批节点
        },
        # 已批准的报销单
        {
            "name": "办公用品报销",
            "description": "购买办公用品报销",
            "template_id": report_template.id if report_template else 1,
            "created_by_id": user2.id if user2 else 1,
            "data": {
                "报销金额": 800,
                "报销类型": "办公用品",
                "报销事由": "购买打印纸、笔和文件夹",
                "报销凭证": "office_receipt.jpg"
            },
            "status": "approved",
            "submitted": True,
            "workflow_id": report_workflow.id if report_workflow else 1,
            "current_node_id": 4  # 结束节点
        },
        # 已拒绝的报销单
        {
            "name": "其他费用报销",
            "description": "其他费用报销申请",
            "template_id": report_template.id if report_template else 1,
            "created_by_id": user1.id if user1 else 1,
            "data": {
                "报销金额": 3000,
                "报销类型": "其他",
                "报销事由": "团建活动费用",
                "报销凭证": "team_receipt.jpg"
            },
            "status": "rejected",
            "submitted": True,
            "workflow_id": report_workflow.id if report_workflow else 1,
            "current_node_id": 2  # 部门经理审批节点
        },
        # 未提交的报销单
        {
            "name": "招待费报销",
            "description": "客户招待费用报销",
            "template_id": report_template.id if report_template else 1,
            "created_by_id": user2.id if user2 else 1,
            "data": {
                "报销金额": 1500,
                "报销类型": "招待费",
                "报销事由": "客户洽谈",
                "报销凭证": ""
            },
            "status": "draft",
            "submitted": False
        },
        # 已提交待审批的请假单
        {
            "name": "年假申请",
            "description": "年假申请",
            "template_id": leave_template.id if leave_template else 2,
            "created_by_id": user1.id if user1 else 1,
            "data": {
                "请假类型": "年假",
                "开始日期": datetime.now().date().isoformat(),
                "结束日期": (datetime.now() + timedelta(days=3)).date().isoformat(),
                "请假天数": 3,
                "请假原因": "休息放松"
            },
            "status": "submitted",
            "submitted": True,
            "workflow_id": leave_workflow.id if leave_workflow else 2,
            "current_node_id": 2  # 部门经理审批节点
        },
        # 无需审批的工作日报
        {
            "name": "2023年6月1日工作日报",
            "description": "日常工作汇报",
            "template_id": daily_template.id if daily_template else 3,
            "created_by_id": user1.id if user1 else 1,
            "data": {
                "日期": "2023-06-01",
                "今日工作内容": "1. 完成项目文档编写\n2. 参加项目例会\n3. 解决客户反馈问题",
                "明日工作计划": "1. 继续完善项目文档\n2. 准备演示材料",
                "工作疑难问题": ""
            },
            "status": "completed",
            "submitted": True
        },
        # 普通工作日报2
        {
            "name": "2023年6月2日工作日报",
            "description": "日常工作汇报",
            "template_id": daily_template.id if daily_template else 3,
            "created_by_id": user2.id if user2 else 1,
            "data": {
                "日期": "2023-06-02",
                "今日工作内容": "1. 设计系统架构\n2. 编写技术方案\n3. 解决系统问题",
                "明日工作计划": "1. 开始系统开发\n2. 准备技术培训",
                "工作疑难问题": "系统性能优化问题"
            },
            "status": "completed",
            "submitted": True
        }
    ]
    
    for ledger_data in ledgers:
        ledger_name = ledger_data["name"]
        ledger = db.query(models.Ledger).filter(
            models.Ledger.name == ledger_name,
            models.Ledger.created_by_id == ledger_data["created_by_id"]
        ).first()
        
        if not ledger:
            workflow_id = ledger_data.pop("workflow_id", None)
            current_node_id = ledger_data.pop("current_node_id", None)
            
            ledger = models.Ledger(**ledger_data)
            db.add(ledger)
            db.flush()
            
            # 如果已提交且有工作流，创建工作流实例
            if ledger.submitted and workflow_id:
                workflow_instance = models.WorkflowInstance(
                    workflow_id=workflow_id,
                    ledger_id=ledger.id,
                    current_node_id=current_node_id,
                    status=ledger.status
                )
                db.add(workflow_instance)
                
                # 创建审计日志
                audit_log = models.AuditLog(
                    action="submit",
                    resource_type="ledger",
                    resource_id=ledger.id,
                    user_id=ledger.created_by_id,
                    status_before="draft",
                    status_after="submitted",
                    comment="提交审批"
                )
                db.add(audit_log)
                
                # 如果状态是approved或rejected，再添加一条审批日志
                if ledger.status == "approved":
                    approver_id = admin_user.id if admin_user else 1
                    audit_log = models.AuditLog(
                        action="approve",
                        resource_type="ledger",
                        resource_id=ledger.id,
                        user_id=approver_id,
                        status_before="submitted",
                        status_after="approved",
                        comment="审批通过"
                    )
                    db.add(audit_log)
                
                elif ledger.status == "rejected":
                    approver_id = admin_user.id if admin_user else 1
                    audit_log = models.AuditLog(
                        action="reject",
                        resource_type="ledger",
                        resource_id=ledger.id,
                        user_id=approver_id,
                        status_before="submitted",
                        status_after="rejected",
                        comment="预算超支，请调整后重新提交"
                    )
                    db.add(audit_log)
            
            logger.info(f"创建测试台账: {ledger_name}")


if __name__ == "__main__":
    insert_test_data() 