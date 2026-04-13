from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.auto_fill_trigger_config import AutoFillTriggerConfig
from app.schemas.auto_fill_trigger_config import (
    AutoFillTriggerConfigCreate,
    AutoFillTriggerConfigUpdate,
)


class CRUDAutoFillTriggerConfig(
    CRUDBase[AutoFillTriggerConfig, AutoFillTriggerConfigCreate, AutoFillTriggerConfigUpdate]
):
    def get_by_field_name(
        self, db: Session, *, field_name: str
    ) -> Optional[AutoFillTriggerConfig]:
        return (
            db.query(AutoFillTriggerConfig)
            .filter(
                AutoFillTriggerConfig.field_name == field_name,
                AutoFillTriggerConfig.enabled == True,
            )
            .first()
        )


auto_fill_trigger_config = CRUDAutoFillTriggerConfig(AutoFillTriggerConfig)
