"""
portrait 消防演练 schema (PRD §10.2 F2-F4)
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DrillCreate(BaseModel):
    """F2 演练登记: 活动信息 + 参与人员"""
    activity_date: date = Field(..., description="活动日期")
    drill_type: str = Field(..., description="类型: 演练/培训/应急疏散")
    location: str = Field(..., max_length=128, description="地点")
    duration_minutes: Optional[int] = Field(None, ge=0, description="时长(分钟)")
    # 参与人员勾选表: ehr_id 列表, 全部视为"已参与"
    participant_ehr_ids: list[str] = Field(default_factory=list)


class DrillUpdate(BaseModel):
    activity_date: Optional[date] = None
    drill_type: Optional[str] = None
    location: Optional[str] = Field(None, max_length=128)
    duration_minutes: Optional[int] = Field(None, ge=0)


class DrillRecord(BaseModel):
    """活动记录 (不含参与人员明细)"""
    id: int
    activity_date: date
    drill_type: str
    location: str
    duration_minutes: Optional[int] = None
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DrillDetail(DrillRecord):
    """活动详情 + 参与人员"""
    participants: list["DrillParticipant"] = Field(default_factory=list)


class DrillParticipant(BaseModel):
    id: int
    drill_id: int
    ehr_id: str
    name: str
    participated: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 矩阵视图 (F4)
# ---------------------------------------------------------------------------
class MatrixCell(BaseModel):
    """矩阵单元格"""
    participated: bool
    value: str  # "参与"/"未参与"


class MatrixRow(BaseModel):
    """矩阵行 = 一名员工"""
    user_id: int
    ehr_id: str
    name: str
    team_name: str
    position: str
    cells: list[MatrixCell]
    participated_count: int  # 合计


class DrillMatrix(BaseModel):
    """矩阵响应:
      columns: 每场活动 {drill_id, activity_date, drill_type, location}
      rows:    每名员工一行
    """
    columns: list[dict]
    rows: list[MatrixRow]
    total_drills: int
    total_participants: int


# ---------------------------------------------------------------------------
# 批量导入 (F3)
# ---------------------------------------------------------------------------
class DrillImportRow(BaseModel):
    """批量导入 Excel 行 (F3, 6 列)"""
    row_number: int
    activity_date: date
    drill_type: str
    location: str
    ehr_id: str
    name: str
    participated: bool


class DrillImportSummary(BaseModel):
    """批量导入结果 (Rule 12: 失败显性化)"""
    success_count: int
    failed_count: int
    failed_rows: list[dict]
