"""
创建workflow_node_approvers表
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./taizhang.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 执行迁移
def run_migration():
    # 创建workflow_node_approvers表
    conn = engine.connect()
    conn.execute(text("""
    CREATE TABLE workflow_node_approvers (
        workflow_node_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (workflow_node_id, user_id),
        FOREIGN KEY(workflow_node_id) REFERENCES workflow_nodes (id),
        FOREIGN KEY(user_id) REFERENCES users (id)
    )
    """))
    conn.commit()
    conn.close()
    print("成功创建workflow_node_approvers表")

if __name__ == "__main__":
    run_migration() 