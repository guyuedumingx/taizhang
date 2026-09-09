from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.crud.base import CRUDBase
from app.models.ledger import Ledger
from app.schemas.ledger import LedgerCreate, LedgerUpdate

class CRUDLedger(CRUDBase[Ledger, LedgerCreate, LedgerUpdate]):
    def create(self, db: Session, *, obj_in: LedgerCreate, created_by_id: int, updated_by_id: int) -> Ledger:
        """创建台账，包含创建者和更新者ID"""
        from fastapi.encoders import jsonable_encoder
        obj_in_data = jsonable_encoder(obj_in)
        
        db_obj = self.model(**obj_in_data)
        db_obj.created_by_id = created_by_id
        db_obj.updated_by_id = updated_by_id
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: Ledger, 
        obj_in: Union[LedgerUpdate, Dict[str, Any]],
        updated_by_id: int
    ) -> Ledger:
        """更新台账，包含更新者ID"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        # # 处理 title 字段，兼容旧代码
        # if "title" in update_data and update_data["title"] is not None:
        #     update_data["name"] = update_data.pop("title")
            
        # 更新 updated_by_id
        update_data["updated_by_id"] = updated_by_id
            
        return super().update(db, db_obj=db_obj, obj_in=update_data)
        
    def get_by_template(self, db: Session, *, template_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(Ledger.template_id == template_id).offset(skip).limit(limit).all()
    
    def get_by_team(self, db: Session, *, team_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(Ledger.team_id == team_id).offset(skip).limit(limit).all()
    
    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Ledger]:
        return db.query(Ledger).filter(
            or_(
                Ledger.created_by_id == user_id,
                Ledger.current_approver_id == user_id
            )
        ).offset(skip).limit(limit).all()

    def get_existing_unique_keys(
        self,
        db: Session,
        *,
        template_id: int,
        key_fields: List[str],
    ) -> Dict[str, int]:
        """
        查库内已有的 unique_keys 组合值,返回 {key_value: ledger_id} 映射。
        用于导入预校验时检测「与库内已有台账重复」。

        key_fields 是字段 label 列表(与 Ledger.data JSON 中的键一致)。

        SQLite 用 json_extract;Oracle 12c+ 用 JSON_VALUE;低版本 Oracle
        回退到 dbms_lob.substr 字符串匹配(性能较差,建议 Oracle 12c+)。
        """
        if not key_fields:
            return {}

        # SQLite 的 JSON 列实际存储为 TEXT(带 ensure_ascii=True 的转义形式),
        # json_extract 对中文键名的处理在某些 SQLite 版本下不稳定,
        # 这里直接用 dbapi 层面读出后 Python 解析,稳妥且兼容 Oracle 低版本。
        sql = (
            f"SELECT id, data FROM ledgers "
            f"WHERE template_id = :tid AND data IS NOT NULL"
        )

        rows = db.execute(text(sql), {"tid": template_id}).fetchall()
        result: Dict[str, int] = {}
        import json as _json
        for ledger_id, data in rows:
            if isinstance(data, str):
                try:
                    data = _json.loads(data)
                except Exception:
                    continue
            if not isinstance(data, dict):
                continue
            key_value = "||".join(str(data.get(f) or "") for f in key_fields)
            result[key_value] = ledger_id
        return result

ledger = CRUDLedger(Ledger)
