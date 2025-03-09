"""
添加multi_approve_type和need_select_next_approver列到workflow_nodes表
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./taizhang.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 执行迁移
def run_migration():
    # 添加multi_approve_type列
    conn = engine.connect()
    conn.execute(text("ALTER TABLE workflow_nodes ADD COLUMN multi_approve_type VARCHAR DEFAULT 'any'"))
    conn.execute(text("ALTER TABLE workflow_nodes ADD COLUMN need_select_next_approver BOOLEAN DEFAULT 0"))
    conn.commit()
    conn.close()
    print("成功添加multi_approve_type和need_select_next_approver列到workflow_nodes表")

if __name__ == "__main__":
    run_migration() 