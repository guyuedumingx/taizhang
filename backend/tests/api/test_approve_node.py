import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app import crud, models
from app.models.workflow import ApprovalStatus

def test_approve_node():
    """测试审批节点功能"""
    db = SessionLocal()
    try:
        # 获取工作流实例
        instance_id = 9  # 根据实际情况修改
        instance = crud.workflow_instance.get(db, id=instance_id)
        if not instance:
            print(f"工作流实例不存在: {instance_id}")
            return
        
        print(f"工作流实例状态: {instance.status}")
        print(f"当前节点ID: {instance.current_node_id}")
        
        # 获取当前节点
        node_id = instance.current_node_id
        if not node_id:
            print("当前节点ID为空")
            return
            
        current_node = db.query(models.WorkflowInstanceNode).filter(
            models.WorkflowInstanceNode.id == node_id
        ).first()
        
        if not current_node:
            print(f"节点不存在: {node_id}")
            return
            
        print(f"当前节点状态: {current_node.status}")
        print(f"当前节点工作流节点ID: {current_node.workflow_node_id}")
        
        # 获取工作流节点定义
        workflow_node = db.query(models.WorkflowNode).filter(
            models.WorkflowNode.id == current_node.workflow_node_id
        ).first()
        
        if not workflow_node:
            print(f"工作流节点不存在: {current_node.workflow_node_id}")
            return
            
        print(f"工作流节点类型: {workflow_node.node_type}")
        print(f"工作流节点顺序: {workflow_node.order_index}")
        
        # 直接调用CRUD方法进行审批
        user_id = 1  # 管理员用户ID
        comment = "测试审批通过"
        
        result = crud.workflow_instance.approve_current_node(
            db,
            instance_id=instance_id,
            user_id=user_id,
            comment=comment,
            next_approver_id=None
        )
        
        print(f"审批结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        import traceback
        print(f"测试过程中发生错误: {str(e)}")
        print(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    test_approve_node() 