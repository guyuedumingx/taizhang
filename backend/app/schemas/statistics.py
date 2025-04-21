from pydantic import BaseModel
from typing import List
from app.schemas.ledger import Ledger
from app.schemas.template import Template


class OverviewResponse(BaseModel):
    users_count: int
    teams_count: int
    ledgers: List[Ledger]
    templates: List[Template]

    class Config:
        orm_mode = True
        from_attributes = True