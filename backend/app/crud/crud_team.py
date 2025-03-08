from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate

class CRUDTeam(CRUDBase[Team, TeamCreate, TeamUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Team]:
        return db.query(Team).filter(Team.name == name).first()

team = CRUDTeam(Team)
