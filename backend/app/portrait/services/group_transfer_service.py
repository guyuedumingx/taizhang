"""
portrait G7 组员调换历史 service (PRD §11.4)

核心不变量:
1. `leave_date IS NULL` = 该记录描述的组**目前仍有效**。每次调组 = 关闭全部开区间
   + 开一条新的 → 任何时刻**最多 1 条开区间记录**。
2. `record_transfer` **只 flush, 绝不 commit** —— 事务边界由调用方已有的 db.commit()
   收口, 保证 `user.team_id` 与历史记录**原子生效**。
3. 不接收 `from_team_id` 参数, `from_team_id` 一律在调用时刻从 `user.team_id` 现读,
   调用方不可能传错。
4. **授权一律比对 team_id 整数, 绝不比对组名字符串。** teams 表允许重名 (开发库里
   有 26 个都叫「外组」), 按名字过滤会让同名组的组长互相看到对方的记录。
   from_group / to_group 只用于展示 —— 组改名后历史记录仍显示当时的组名。
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models
from app.portrait import models as portrait_models
from app.portrait.models._base import beijing_now
from app.services.team_service import TeamService

# to_group 是 nullable=False, 但退组 (remove_user_from_team) 会把 team_id 置 None。
# 用占位值而不是 nullable, 避免改模型 (团队空组名不好认, 且名字列还要留作展示)。
GROUP_UNASSIGNED = "未分组"


def _team_name(db: Session, team_id: Optional[int]) -> str:
    """team_id → 组名 (仅用于展示); None → 占位值「未分组」"""
    if team_id is None:
        return GROUP_UNASSIGNED
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=400, detail=f"团队 id={team_id} 不存在, 无法记录调组历史"
        )
    return team.name


def _resolve_operator(db: Session, operator_user_id: Optional[int]) -> models.User:
    """操作人必须存在 —— operator 三列非空, 不能伪造也不能静默跳过 (Rule 12)"""
    if operator_user_id is None:
        raise HTTPException(status_code=400, detail="记录调组历史必须提供操作人 (operator_user_id)")
    operator = db.query(models.User).filter(models.User.id == operator_user_id).first()
    if not operator:
        raise HTTPException(
            status_code=400, detail=f"操作人 id={operator_user_id} 不存在, 无法记录调组历史"
        )
    return operator


def record_transfer(
    db: Session,
    *,
    user: models.User,
    to_team_id: Optional[int],
    operator_user_id: Optional[int],
    reason: Optional[str] = None,
    remark: Optional[str] = None,
    transfer_date: Optional[datetime] = None,
) -> Optional[portrait_models.GroupTransferHistory]:
    """记录一次调组。

    **必须在调用方改 `user.team_id` 之前调用** —— from_team_id 从 user.team_id 现读。

    只 `flush` 不 `commit`: 与 user.team_id 的变更同属调用方事务。

    返回新记录; 若组别未变 (短路) 则返回 None 且**不写库** ——
    前端 UserManagement 每次编辑都会提交 team_id, 没这个短路改个名字就会伪造一条调组。
    """
    from_team_id = user.team_id
    if from_team_id == to_team_id:
        return None

    # 先解析所有名字/操作人, 再动任何东西 —— 保证零半截写入
    from_group = _team_name(db, from_team_id)
    to_group = _team_name(db, to_team_id)
    operator = _resolve_operator(db, operator_user_id)

    now = transfer_date or beijing_now()

    # 关闭全部开区间 (用 .all() 不用 .first(): 保证 "最多 1 条开区间" 不变量永不被破坏)
    open_records = (
        db.query(portrait_models.GroupTransferHistory)
        .filter(
            portrait_models.GroupTransferHistory.user_id == user.id,
            portrait_models.GroupTransferHistory.leave_date.is_(None),
        )
        .all()
    )
    for record in open_records:
        record.leave_date = now

    new_record = portrait_models.GroupTransferHistory(
        user_id=user.id,
        ehr_no=user.ehr_id,
        from_group=from_group,
        to_group=to_group,
        from_team_id=from_team_id,
        to_team_id=to_team_id,
        transfer_date=now,
        leave_date=None,
        operator_user_id=operator.id,
        operator_ehr_no=operator.ehr_id,
        operator_name=operator.name or operator.username or "",
        reason=reason,
        remark=remark,
    )
    db.add(new_record)
    db.flush()  # 事务边界留给调用方
    return new_record


class GroupTransferService:
    @staticmethod
    def _viewer_team_id(db: Session, viewer: models.User) -> int:
        """组长的可见范围 = 本组 team_id。

        没有组 / 组已删 / 不是本组组长 → 403, **不静默降级成看全部**
        (否则等于给所有人开放)。

        决策 1: 组长判据收口到 TeamService.is_leader (是所在组的 leader_id)。
        """
        if not viewer.team_id:
            raise HTTPException(status_code=403, detail="仅管理员或组长可查看组员调换历史")
        if not TeamService.is_leader(db, viewer):
            raise HTTPException(status_code=403, detail="仅管理员或组长可查看组员调换历史")
        team = db.query(models.Team).filter(models.Team.id == viewer.team_id).first()
        if not team:
            raise HTTPException(
                status_code=403, detail="当前用户所属团队不存在, 无法确定可见范围"
            )
        return viewer.team_id

    @staticmethod
    def list_records(
        db: Session,
        *,
        viewer: models.User,
        skip: int = 0,
        limit: int = 50,
        ehr_id: Optional[str] = None,
        name: Optional[str] = None,
        year: Optional[int] = None,
        is_current: Optional[bool] = None,
    ) -> tuple[list[portrait_models.GroupTransferHistory], int]:
        """admin 全员 / 组长本组相关 (from_team_id 或 to_team_id 为本组)。

        筛外组 EHR 返回**空列表而非 403** —— 不泄露该 EHR 是否存在。
        """
        query = db.query(portrait_models.GroupTransferHistory)
        if not viewer.is_superuser:
            team_id = GroupTransferService._viewer_team_id(db, viewer)
            query = query.filter(
                or_(
                    portrait_models.GroupTransferHistory.from_team_id == team_id,
                    portrait_models.GroupTransferHistory.to_team_id == team_id,
                )
            )

        if ehr_id:
            query = query.filter(portrait_models.GroupTransferHistory.ehr_no == ehr_id)
        if name:
            matched_ids = [
                row[0]
                for row in db.query(models.User.id)
                .filter(models.User.name.ilike(f"%{name}%"))
                .all()
            ]
            query = query.filter(portrait_models.GroupTransferHistory.user_id.in_(matched_ids))
        if year:
            # 用区间而不是 strftime('%Y', ...) —— 后者是 SQLite 专有语法, 换 PG 会炸
            query = query.filter(
                portrait_models.GroupTransferHistory.transfer_date >= datetime(year, 1, 1),
                portrait_models.GroupTransferHistory.transfer_date < datetime(year + 1, 1, 1),
            )
        if is_current is not None:
            query = query.filter(
                portrait_models.GroupTransferHistory.leave_date.is_(None)
                if is_current
                else portrait_models.GroupTransferHistory.leave_date.isnot(None)
            )

        total = query.count()
        items = (
            query.order_by(
                portrait_models.GroupTransferHistory.transfer_date.desc(),
                portrait_models.GroupTransferHistory.id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    @staticmethod
    def delete(db: Session, *, record: portrait_models.GroupTransferHistory) -> None:
        """删除记录 (admin 纠错)。

        **禁止删开区间记录**: 开区间是「此人在此组」的唯一凭证, 删了组长就再也
        看不到他。正确纠错方式是「把他调回去」—— 系统会自动关闭错误记录,
        再删这条闭区间的。
        """
        if record.leave_date is None:
            raise HTTPException(
                status_code=400,
                detail="无法删除「当前在组」的记录, 请先把他调回正确组别, 系统会自动关闭错误记录",
            )
        db.delete(record)
        db.commit()


group_transfer_service = GroupTransferService()

# Phase 4: 组员调换留痕改为事件注册 —— 核心层 (team/user service) 只 dispatch
# 中性事件名, 不再反向 import 本模块; 单独部署台账核心时本模块不加载也零影响。
from app.services import domain_events as _domain_events


def _on_user_team_changed(db, *, user, to_team_id, operator_user_id):
    record_transfer(db, user=user, to_team_id=to_team_id, operator_user_id=operator_user_id)


_domain_events.register(_domain_events.EVENT_USER_TEAM_CHANGED, _on_user_team_changed)
