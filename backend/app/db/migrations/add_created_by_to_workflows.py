"""
添加created_by列到workflows表
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库连接
SQLALCHEMY_DATABASE_URL = "sqlite:///./taizhang.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 执行迁移
def run_migration():
    # 添加created_by列
    conn = engine.connect()
    conn.execute(text("ALTER TABLE workflows ADD COLUMN created_by INTEGER REFERENCES users(id)"))
    conn.commit()
    conn.close()
    print("成功添加created_by列到workflows表")

if __name__ == "__main__":
    run_migration() 