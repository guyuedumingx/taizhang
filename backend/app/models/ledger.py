from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Ledger(Base):
    __tablename__ = "ledgers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft, active, completed
    
    # 外键
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 数据，存储为JSON
    data = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    team = relationship("Team", back_populates="ledgers")
    template = relationship("Template", back_populates="ledgers")
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_ledgers")
    updater = relationship("User", foreign_keys=[updated_by_id], back_populates="updated_ledgers") 