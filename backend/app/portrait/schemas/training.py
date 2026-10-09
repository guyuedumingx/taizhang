"""
portrait 培训记录 schema (PRD §10.3)
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingRecordBase(BaseModel):
    training_name: str = Field(..., max_length=128)
    training_at: datetime
    training_type: str = Field(..., max_length=32)
    institution: str = Field(..., max_length=128)
    certificate_no: Optional[str] = Field(None, max_length=64)
    valid_until: Optional[date] = None


class TrainingRecordCreate(TrainingRecordBase):
    """管理员录入/批量导入使用"""
    ehr_id: str = Field(..., pattern=r"^\d{7}$", description="员工 EHR 号, 恰好 7 位数字")


class TrainingRecordUpdate(BaseModel):
    training_name: Optional[str] = Field(None, max_length=128)
    training_at: Optional[datetime] = None
    training_type: Optional[str] = Field(None, max_length=32)
    institution: Optional[str] = Field(None, max_length=128)
    certificate_no: Optional[str] = Field(None, max_length=64)
    valid_until: Optional[date] = None


class TrainingRecord(TrainingRecordBase):
    id: int
    ehr_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingImportSummary(BaseModel):
    """批量导入结果汇总 (Rule 12: 不吞错, 跳过的行数和原因必须暴露)"""
    success_count: int
    failed_count: int
    failed_rows: list[dict]  # [{row_number, ehr_id, reason}]


class TrainingImportRow(BaseModel):
    """批量导入 Excel 行解析结果 (内部用)"""
    row_number: int
    ehr_id: str
    training_name: str
    training_at: datetime
    training_type: str
    institution: str
    certificate_no: Optional[str] = None
    valid_until: Optional[date] = None