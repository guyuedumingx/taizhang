from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class FieldValue(Base):
    __tablename__ = "field_values"

    id = Column(Integer, primary_key=True, index=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.id", ondelete="CASCADE"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id", ondelete="CASCADE"), nullable=False)
    value = Column(Text, nullable=True)
    
    # 关系
    ledger = relationship("Ledger", back_populates="field_values")
    field = relationship("Field", back_populates="field_values") 