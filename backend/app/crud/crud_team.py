from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.team import Team
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate

class CRUDTeam(CRUDBase[Team, TeamCreate, TeamUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Team]:
        return db.query(Team).filter(Team.name == name).first()
        
    def get_team_members(self, db: Session, *, team_id: int) -> List[User]:
        """获取团队成员"""
        return db.query(User).filter(User.team_id == team_id).all()

team = CRUDTeam(Team)
