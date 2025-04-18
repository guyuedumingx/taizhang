from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    ehr_id = Column(String(7), unique=True, index=True, nullable=False)  # 7位数字的EHR号
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    department = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    last_password_change = Column(DateTime, default=datetime.now)
    
    # 关系
    team = relationship("Team", back_populates="members", foreign_keys=[team_id])
    created_ledgers = relationship("Ledger", foreign_keys="[Ledger.created_by_id]", back_populates="creator")
    updated_ledgers = relationship("Ledger", foreign_keys="[Ledger.updated_by_id]", back_populates="updater") 
    # workflow_nodes = relationship("WorkflowNode", secondary="workflow_node_approvers", back_populates="approvers")

    def __repr__(self):
        return f"<User {self.username}>"
