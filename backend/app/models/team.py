from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    department = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 关系
    members = relationship("User", back_populates="team", foreign_keys="[User.team_id]")
    leader = relationship("User", foreign_keys=[leader_id])
    ledgers = relationship("Ledger", back_populates="team") 