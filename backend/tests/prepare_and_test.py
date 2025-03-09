#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
准备测试数据并运行API测试

这个脚本首先准备测试数据库中的必要数据，然后运行API测试
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加当前目录到路径
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

from app.main import app
from app.api.deps import get_db, get_current_active_user
from app import models, crud, schemas
from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.core.security import get_password_hash

client = TestClient(app)

def create_test_admin():
    """创建测试管理员用户"""
    print("创建测试管理员用户...")
    db = SessionLocal()
    
    # 检查是否已存在
    admin = crud.user.get_by_username(db, username="testadmin")
    
    if not admin:
        # 直接创建用户模型
        admin = models.User(
            username="testadmin",
            ehr_id="1234567",
            name="测试管理员",
            hashed_password=get_password_hash("testadmin123"),
            is_active=True,
            is_superuser=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"创建测试管理员成功: {admin.id}")
    else:
        print(f"测试管理员已存在: {admin.id}")

    db.close()
    return admin

def create_test_normal_user():
    """创建测试普通用户"""
    print("创建测试普通用户...")
    db = SessionLocal()
    
    # 检查是否已存在
    user = crud.user.get_by_username(db, username="testuser")
    
    if not user:
        # 直接创建用户模型
        user = models.User(
            username="testuser",
            ehr_id="8765432",
            name="测试用户",
            hashed_password=get_password_hash("testuser123"),
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"创建测试普通用户成功: {user.id}")
    else:
        print(f"测试普通用户已存在: {user.id}")
    
    db.close()
    return user

def create_test_template():
    """创建测试模板"""
    print("创建测试模板...")
    db = SessionLocal()
    
    try:
        # 检查是否已存在模板
        templates = db.query(models.Template).limit(10).all()
        if templates and len(templates) > 0:
            print(f"已存在模板: {len(templates)}个")
            template = templates[0]
        else:
            # 获取管理员用户
            admin = db.query(models.User).filter(models.User.is_superuser == True).first()
            if not admin:
                print("错误: 找不到管理员用户")
                return None
                
            # 直接创建模板模型
            template = models.Template(
                name="测试台账模板",
                description="用于API测试的台账模板",
                department="测试部门",
                is_system=False,
                created_by_id=admin.id,
                updated_by_id=admin.id
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            print(f"创建测试模板成功: {template.id}")
            
            # 创建字段
            fields = [
                models.Field(
                    name="title",
                    label="标题",
                    type="string",
                    required=True,
                    order=1,
                    template_id=template.id
                ),
                models.Field(
                    name="description",
                    label="描述",
                    type="text",
                    required=False,
                    order=2,
                    template_id=template.id
                ),
                models.Field(
                    name="amount",
                    label="金额",
                    type="number",
                    required=True,
                    order=3,
                    template_id=template.id
                )
            ]
            
            for field in fields:
                db.add(field)
            
            db.commit()
            print(f"创建测试模板字段成功")
    except Exception as e:
        print(f"创建模板时出错: {e}")
        db.rollback()
        template = None
    finally:
        db.close()
        
    return template

def create_test_workflow(template_id):
    """创建测试工作流"""
    print("创建测试工作流...")
    db = SessionLocal()
    
    try:
        # 检查是否已存在工作流
        workflows = db.query(models.Workflow).limit(10).all()
        if workflows and len(workflows) > 0:
            print(f"已存在工作流: {len(workflows)}个")
            workflow = workflows[0]
        else:
            # 获取管理员用户
            admin = db.query(models.User).filter(models.User.is_superuser == True).first()
            if not admin:
                print("错误: 找不到管理员用户")
                return None
                
            # 直接创建工作流模型
            workflow = models.Workflow(
                name="测试工作流",
                description="用于API测试的工作流",
                template_id=template_id,
                is_active=True,
                created_by_id=admin.id,
                updated_by_id=admin.id
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            print(f"创建测试工作流成功: {workflow.id}")
            
            # 创建工作流节点
            nodes = [
                models.WorkflowNode(
                    workflow_id=workflow.id,
                    name="开始节点",
                    description="工作流开始",
                    node_type="start",
                    order_index=0
                ),
                models.WorkflowNode(
                    workflow_id=workflow.id,
                    name="审批节点",
                    description="管理员审批",
                    node_type="approval",
                    approver_user_id=admin.id,
                    order_index=1
                ),
                models.WorkflowNode(
                    workflow_id=workflow.id,
                    name="结束节点",
                    description="工作流结束",
                    node_type="end",
                    order_index=2,
                    is_final=True
                )
            ]
            
            for node in nodes:
                db.add(node)
            
            db.commit()
            print(f"创建工作流节点成功")
    except Exception as e:
        print(f"创建工作流时出错: {e}")
        db.rollback()
        workflow = None
    finally:
        db.close()
        
    return workflow

def create_test_ledger(template_id):
    """创建测试台账"""
    print("创建测试台账...")
    db = SessionLocal()
    
    try:
        # 检查是否已存在台账
        ledgers = db.query(models.Ledger).limit(10).all()
        if ledgers and len(ledgers) > 0:
            print(f"已存在台账: {len(ledgers)}个")
            ledger = ledgers[0]
        else:
            # 获取管理员用户
            admin = db.query(models.User).filter(models.User.is_superuser == True).first()
            if not admin:
                print("错误: 找不到管理员用户")
                return None
                
            # 直接创建台账模型
            ledger = models.Ledger(
                name="测试台账",
                description="用于API测试的台账",
                template_id=template_id,
                status="draft",
                created_by_id=admin.id,
                updated_by_id=admin.id
            )
            db.add(ledger)
            db.commit()
            db.refresh(ledger)
            print(f"创建测试台账成功: {ledger.id}")
            
            # 获取模板字段
            fields = db.query(models.Field).filter(models.Field.template_id == template_id).all()
            
            # 创建字段值
            field_values = []
            for field in fields:
                value = None
                if field.name == "title":
                    value = "测试标题"
                elif field.name == "description":
                    value = "这是一个测试描述"
                elif field.name == "amount":
                    value = "100.0"
                
                if value is not None:
                    field_value = models.FieldValue(
                        ledger_id=ledger.id,
                        field_id=field.id,
                        value=value
                    )
                    field_values.append(field_value)
            
            for field_value in field_values:
                db.add(field_value)
            
            db.commit()
            print(f"创建台账字段值成功")
    except Exception as e:
        print(f"创建台账时出错: {e}")
        db.rollback()
        ledger = None
    finally:
        db.close()
        
    return ledger

def prepare_test_data():
    """准备测试数据"""
    print("\n===== 开始准备测试数据 =====\n")
    
    # 使用一个会话处理所有数据创建
    db = SessionLocal()
    
    try:
        # 创建必要的测试数据
        admin = create_test_admin()
        user = create_test_normal_user()
        
        if admin:
            # 检查是否已存在模板
            templates = db.query(models.Template).limit(10).all()
            if templates and len(templates) > 0:
                print(f"已存在模板: {len(templates)}个")
                template = templates[0]
            else:
                # 直接创建模板模型
                template = models.Template(
                    name="测试台账模板",
                    description="用于API测试的台账模板",
                    department="测试部门",
                    is_system=False,
                    created_by_id=admin.id,
                    updated_by_id=admin.id
                )
                db.add(template)
                db.commit()
                db.refresh(template)
                print(f"创建测试模板成功: {template.id}")
                
                # 创建字段
                fields = [
                    models.Field(
                        name="title",
                        label="标题",
                        type="string",
                        required=True,
                        order=1,
                        template_id=template.id
                    ),
                    models.Field(
                        name="description",
                        label="描述",
                        type="text",
                        required=False,
                        order=2,
                        template_id=template.id
                    ),
                    models.Field(
                        name="amount",
                        label="金额",
                        type="number",
                        required=True,
                        order=3,
                        template_id=template.id
                    )
                ]
                
                for field in fields:
                    db.add(field)
                
                db.commit()
                print(f"创建测试模板字段成功")
            
            if template:
                # 检查是否已存在工作流
                workflows = db.query(models.Workflow).limit(10).all()
                if workflows and len(workflows) > 0:
                    print(f"已存在工作流: {len(workflows)}个")
                    workflow = workflows[0]
                else:
                    # 直接创建工作流模型
                    workflow = models.Workflow(
                        name="测试工作流",
                        description="用于API测试的工作流",
                        template_id=template.id,
                        is_active=True
                    )
                    db.add(workflow)
                    db.commit()
                    db.refresh(workflow)
                    print(f"创建测试工作流成功: {workflow.id}")
                    
                    # 创建工作流节点
                    nodes = [
                        models.WorkflowNode(
                            workflow_id=workflow.id,
                            name="开始节点",
                            description="工作流开始",
                            node_type="start",
                            order_index=0
                        ),
                        models.WorkflowNode(
                            workflow_id=workflow.id,
                            name="审批节点",
                            description="管理员审批",
                            node_type="approval",
                            approver_user_id=admin.id,
                            order_index=1
                        ),
                        models.WorkflowNode(
                            workflow_id=workflow.id,
                            name="结束节点",
                            description="工作流结束",
                            node_type="end",
                            order_index=2,
                            is_final=True
                        )
                    ]
                    
                    for node in nodes:
                        db.add(node)
                    
                    db.commit()
                    print(f"创建工作流节点成功")
                
                if workflow:
                    # 检查是否已存在台账
                    ledgers = db.query(models.Ledger).limit(10).all()
                    if ledgers and len(ledgers) > 0:
                        print(f"已存在台账: {len(ledgers)}个")
                        ledger = ledgers[0]
                    else:
                        # 直接创建台账模型
                        ledger = models.Ledger(
                            name="测试台账",
                            description="用于API测试的台账",
                            template_id=template.id,
                            status="draft",
                            created_by_id=admin.id,
                            updated_by_id=admin.id
                        )
                        db.add(ledger)
                        db.commit()
                        db.refresh(ledger)
                        print(f"创建测试台账成功: {ledger.id}")
                        
                        # 获取模板字段
                        fields = db.query(models.Field).filter(models.Field.template_id == template.id).all()
                        
                        # 创建字段值
                        field_values = []
                        for field in fields:
                            value = None
                            if field.name == "title":
                                value = "测试标题"
                            elif field.name == "description":
                                value = "这是一个测试描述"
                            elif field.name == "amount":
                                value = "100.0"
                            
                            if value is not None:
                                field_value = models.FieldValue(
                                    ledger_id=ledger.id,
                                    field_id=field.id,
                                    value=value
                                )
                                field_values.append(field_value)
                        
                        for field_value in field_values:
                            db.add(field_value)
                        
                        db.commit()
                        print(f"创建台账字段值成功")
    except Exception as e:
        print(f"准备测试数据时出错: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n===== 测试数据准备完成 =====\n")

def run_api_tests():
    """运行API测试"""
    print("\n===== 开始运行API测试 =====\n")
    
    # 调用测试运行器来执行API测试
    subprocess.run(["python", "tests/run_api_tests.py", "--run", "all"])
    
    print("\n===== API测试运行完成 =====\n")

def main():
    """主函数"""
    prepare_test_data()
    run_api_tests()

if __name__ == "__main__":
    main() 