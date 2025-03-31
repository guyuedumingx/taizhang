"""
处理workflow与template关系变更的迁移脚本
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey, update, text
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
        # 1. 检查templates表是否有workflow_id列
        has_workflow_id = False
        try:
            result = db.execute(text("PRAGMA table_info(templates)"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            has_workflow_id = 'workflow_id' in column_names
            print(f"templates表的列: {column_names}")
        except Exception as e:
            print(f"检查templates表结构时出错: {str(e)}")
        
        # 2. 如果没有workflow_id列，添加它
        if not has_workflow_id:
            print("添加workflow_id字段到templates表")
            db.execute(text("""
                ALTER TABLE templates 
                ADD COLUMN workflow_id INTEGER REFERENCES workflows(id)
            """))
        else:
            print("templates表已有workflow_id列，跳过添加")
            
        # 3. 检查是否有重复的ledger_id
        print("检查workflow_instances表中是否有重复的ledger_id")
        result = db.execute(text("""
            SELECT ledger_id, COUNT(*) as count 
            FROM workflow_instances 
            GROUP BY ledger_id 
            HAVING count > 1
        """))
        
        duplicates = result.fetchall()
        if duplicates:
            print(f"发现重复的ledger_id: {duplicates}")
            print("请手动解决重复数据问题后再继续")
            return
        else:
            print("没有发现重复的ledger_id，可以继续")
        
        # 4. 迁移数据：workflows.template_id -> templates.workflow_id
        print("查询workflows表中的template_id")
        result = db.execute(text("SELECT id, template_id FROM workflows WHERE template_id IS NOT NULL"))
        workflow_template_pairs = result.fetchall()
        
        print(f"找到{len(workflow_template_pairs)}条需要迁移的数据")
        for workflow_id, template_id in workflow_template_pairs:
            print(f"处理workflow ID: {workflow_id}, template ID: {template_id}")
            db.execute(text(f"UPDATE templates SET workflow_id = {workflow_id} WHERE id = {template_id}"))
        
        # 5. 检查workflows表是否有template_id列
        has_template_id = False
        try:
            result = db.execute(text("PRAGMA table_info(workflows)"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            has_template_id = 'template_id' in column_names
            print(f"workflows表的列: {column_names}")
        except Exception as e:
            print(f"检查workflows表结构时出错: {str(e)}")
        
        # 6. 如果存在template_id列，删除它
        if has_template_id:
            print("删除workflows表中的template_id列")
            try:
                db.execute(text("ALTER TABLE workflows DROP COLUMN template_id"))
                print("template_id列已删除")
            except Exception as e:
                print(f"删除template_id列时出错: {str(e)}")
                print("SQLite可能不支持直接删除列，这在部分SQLite版本中是正常的")
                print("该列将保留但不再使用")
        else:
            print("workflows表没有template_id列，无需删除")
        
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