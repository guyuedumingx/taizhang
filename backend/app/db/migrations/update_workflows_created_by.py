"""
更新workflows表中的created_by列
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./taizhang.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 执行迁移
def run_migration():
    # 更新workflows表中的created_by列
    conn = engine.connect()
    conn.execute(text("UPDATE workflows SET created_by = 1 WHERE created_by IS NULL"))
    conn.commit()
    conn.close()
    print("成功更新workflows表中的created_by列")

if __name__ == "__main__":
    run_migration() 