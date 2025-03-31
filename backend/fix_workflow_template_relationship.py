"""
修复工作流与模板关系的脚本
将之前通过template_id字段关联的关系改为从template端关联
"""

import os
import sys
from sqlalchemy import create_engine, Column, Table, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import Base, SessionLocal, engine
from app.models.workflow import Workflow
from app.models.template import Template

def main():
    print("开始修复工作流与模板的关系...")
    
    # 创建会话
    db = SessionLocal()
    try:
        # 1. 查找所有带有template_id的工作流
        workflows_with_template = db.query(Workflow).filter(Workflow.template_id.isnot(None)).all()
        print(f"找到 {len(workflows_with_template)} 个带有template_id的工作流")
        
        # 2. 为每个工作流找到对应的模板并建立正确的关系
        for workflow in workflows_with_template:
            template = db.query(Template).filter(Template.id == workflow.template_id).first()
            if template:
                print(f"工作流 '{workflow.name}' (ID: {workflow.id}) 关联到模板 '{template.name}' (ID: {template.id})")
                # 检查是否已经在关联列表中
                if workflow not in template.workflows:
                    template.workflows.append(workflow)
                
        # 3. 提交更改
        db.commit()
        print("工作流与模板的关系已经修复")
        
    except Exception as e:
        db.rollback()
        print(f"发生错误: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 