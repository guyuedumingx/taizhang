"""
处理workflow与template关系变更的迁移脚本
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey, update
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def migrate():
    print("开始数据库迁移...")
    
    # 创建数据库连接
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    metadata = MetaData()
    
    # 获取现有表
    templates = Table('templates', metadata, autoload_with=engine)
    workflows = Table('workflows', metadata, autoload_with=engine)
    
    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 添加workflow_id列到templates表
        if 'workflow_id' not in templates.columns:
            print("添加workflow_id字段到templates表")
            db.execute("""
                ALTER TABLE templates 
                ADD COLUMN workflow_id INTEGER REFERENCES workflows(id)
            """)
            
        # 添加unique约束到workflow_instances表的ledger_id列
        print("将ledger_id字段设为唯一约束")
        db.execute("""
            ALTER TABLE workflow_instances
            ADD CONSTRAINT unique_ledger_id UNIQUE (ledger_id)
        """)
        
        # 迁移数据，将template_id的值从workflow表迁移到template表的workflow_id
        print("迁移数据，将template_id的值迁移到workflow_id")
        result = db.execute("SELECT id, template_id FROM workflows WHERE template_id IS NOT NULL")
        workflow_template_pairs = result.fetchall()
        
        for workflow_id, template_id in workflow_template_pairs:
            print(f"处理workflow ID: {workflow_id}, template ID: {template_id}")
            db.execute(f"UPDATE templates SET workflow_id = {workflow_id} WHERE id = {template_id}")
        
        # 删除template_id列
        print("删除workflows表中的template_id列")
        db.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS template_id")
        
        # 提交更改
        db.commit()
        print("数据库迁移完成")
        
    except Exception as e:
        db.rollback()
        print(f"迁移过程中发生错误: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate() 