from typing import Any, List, Optional, Dict
from collections import defaultdict
from app.services import domain_events
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app import models, schemas
from app.utils.logger import LoggerService


class TeamService:
    """团队服务类，处理团队相关的业务逻辑"""

    @staticmethod
    def is_leader(db: Session, user: models.User) -> bool:
        """组长判据（决策 1，2026-10-16）：该用户是其所在组的 ``teams.leader_id``。

        历史上的判据是「``team_id`` 非空」—— 任何员工只要被分了个组就自动获得
        组长权限（能看本组全员档案、能建家访、能审批），这是审计报告 §1.1 里
        多项功能权限过宽的共同根因。

        判据收口到这一个函数，画像各 service 不再各自抄一遍（Rule 8/11）。

        注意：超管**不算**组长 —— 超管的身份由各调用点的 ``is_superuser`` 分支
        单独处理，这里返回 False 以免"超管也是组长"被当成同一件事。
        """
        if user is None or user.is_superuser or user.team_id is None:
            return False
        leader_id = (
            db.query(models.Team.leader_id)
            .filter(models.Team.id == user.team_id)
            .scalar()
        )
        return leader_id is not None and leader_id == user.id

    @staticmethod
    def get_teams_count(db: Session) -> int:
        """获取团队总数"""
        return db.query(models.Team).count()

    @staticmethod
    def get_teams(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[models.Team]:
        """获取团队列表"""
        try:
            # 构建查询
            query = db.query(models.Team)
            
            # 搜索
            if search:
                query = query.filter(models.Team.name.ilike(f"%{search}%"))
            
            # 使用预加载优化查询，避免N+1问题
            query = query.options(
                selectinload(models.Team.leader),  # 预加载负责人
            )
            
            # 分页
            teams = query.offset(skip).limit(limit).all()
            
            # 批量计算每个团队的成员数量（避免N+1查询）
            team_ids = [team.id for team in teams]
            member_counts = defaultdict(int)
            if team_ids:
                member_count_query = db.query(
                    models.User.team_id,
                    func.count(models.User.id).label('count')
                ).filter(
                    models.User.team_id.in_(team_ids)
                ).group_by(models.User.team_id).all()
                
                for team_id, count in member_count_query:
                    member_counts[team_id] = count
            
            # 设置团队信息
            for team in teams:
                try:
                    # 获取成员数量（从批量查询结果获取）
                    team.member_count = member_counts.get(team.id, 0)
                    
                    # 获取团队负责人姓名（已预加载）
                    if team.leader:
                        team.leader_name = team.leader.name
                    else:
                        team.leader_name = None
                except Exception as e:
                    print(f"处理团队 {team.id} 的信息时出错: {e}")
                    team.member_count = 0
                    team.leader_name = None
            
            return teams
        except Exception as e:
            print(f"获取团队列表时出错: {e}")
            return []

    @staticmethod
    def release_leadership_if_left(
        db: Session, user: models.User, old_team_id: Optional[int]
    ) -> None:
        """用户离开某组时, 若他是该组组长则清空该组的 leader_id。

        决策 1: ``teams.leader_id`` 是组长判据的唯一来源。若它继续指向一个
        已经不在本组的人, 会出现"字段说有组长、实际没人是组长"的空转 ——
        管理界面显示的"负责人"与判据不符, 组内家访/审批等组长功能集体瘫掉。
        调用方负责在改 ``user.team_id`` **之前**调用 (此时 old_team_id 仍可读)。
        """
        if old_team_id is None:
            return
        old_team = db.query(models.Team).filter(models.Team.id == old_team_id).first()
        if old_team is not None and old_team.leader_id == user.id:
            old_team.leader_id = None
            db.add(old_team)

    @staticmethod
    def create_team(
        db: Session,
        team_in: schemas.TeamCreate,
        current_user_id: int
    ) -> models.Team:
        """创建新团队

        决策 1 (2026-10-16): 组长身份记在「组」上 (``teams.leader_id``), 且
        组长**必须是本组成员** —— leader_id 指向外组的人, 组的 leader 字段
        就与判据失真。

        因此建组时:
          - 管理员在表单里指定了负责人 (``team_in.leader_id``, 前端
            TeamManagement 的「团队负责人」下拉) → 该人成为本组首任组长,
            并被调入本组 (与 add_user_to_team 同口径: 一人只属一个组)
          - 未指定 → 本组暂无组长 (``leader_id`` 留空), 后续在「编辑团队」
            里指定

        刻意**不做**"创建者自动入组当组长": 那是静默调组 (创建者被动换组),
        且会让新建的组因带成员而无法删除。组内无组长是可观察的中间态,
        静默调组不可察。
        """
        # 检查团队名称是否已存在
        team = db.query(models.Team).filter(models.Team.name == team_in.name).first()
        if team:
            raise HTTPException(
                status_code=400,
                detail="团队名称已存在",
            )

        # 负责人: 管理员指定的那一位 (未指定则本组暂无组长)
        leader = None
        if team_in.leader_id is not None:
            leader = (
                db.query(models.User)
                .filter(models.User.id == team_in.leader_id)
                .first()
            )
            if leader is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"组长用户不存在 (id={team_in.leader_id})",
                )
            if not leader.is_active:
                raise HTTPException(
                    status_code=400,
                    detail="组长用户已停用, 不能指定为组长",
                )

        # 创建团队
        team = models.Team(
            name=team_in.name,
            description=team_in.description,
            department=team_in.department,
            leader_id=leader.id if leader is not None else None,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        # 组长必须是本组成员 → 把负责人调入新组。
        # 走 domain_events 是为了与普通调组共用同一条审计路径 (G7 组员调换历史);
        # 处理器只留痕不赋值, 改 team_id 仍由本函数负责 (与 user_service 同序:
        # 先 dispatch 让处理器读到原组, 再 setattr)。
        if leader is not None and leader.team_id != team.id:
            old_team_id = leader.team_id
            domain_events.dispatch(
                domain_events.EVENT_USER_TEAM_CHANGED,
                db,
                user=leader,
                to_team_id=team.id,
                operator_user_id=current_user_id,
            )
            # 调离原组 → 原组的组长位不能继续挂着他 (否则字段指向外组的人)
            TeamService.release_leadership_if_left(db, leader, old_team_id)
            leader.team_id = team.id
            db.commit()
            db.refresh(leader)

        return team

    @staticmethod
    def get_team(db: Session, team_id: int) -> models.Team:
        """获取团队详情"""
        # 使用预加载优化查询
        team = db.query(models.Team).filter(models.Team.id == team_id).options(
            selectinload(models.Team.leader),  # 预加载负责人
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        # 计算成员数量
        team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
        
        # 获取团队负责人姓名（已预加载）
        if team.leader:
            team.leader_name = team.leader.name
        else:
            team.leader_name = None
        
        return team

    @staticmethod
    def update_team(
        db: Session,
        team_id: int,
        team_in: schemas.TeamUpdate,
        current_user_id: int
    ) -> models.Team:
        """
        更新团队信息
        """
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        # 如果更新团队名称，检查是否已存在
        if team_in.name and team_in.name != team.name:
            existing_team = db.query(models.Team).filter(models.Team.name == team_in.name).first()
            if existing_team:
                raise HTTPException(
                    status_code=400,
                    detail="团队名称已存在",
                )
        
        # 更新团队信息
        update_data = team_in.dict(exclude_unset=True)

        # 决策 1: leader_id 必须指向**本组**的某个人。
        # 组长判据是「该用户是所在组的 leader_id」, 指向外组的人会让两个组的
        # 组长字段同时失真 (Rule 12: 非法状态要拦住, 不能靠下游兜底)。
        # 显式传 null 表示取消组长, 允许。
        if "leader_id" in update_data and update_data["leader_id"] is not None:
            leader_id = update_data["leader_id"]
            leader = db.query(models.User).filter(models.User.id == leader_id).first()
            if leader is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"组长用户不存在 (id={leader_id})",
                )
            if leader.team_id != team_id:
                raise HTTPException(
                    status_code=400,
                    detail="组长必须是本组成员, 请先调入本组再指定",
                )

        # 更新其他字段
        for field, value in update_data.items():
            setattr(team, field, value)

        db.add(team)
        db.commit()
        db.refresh(team)

        return team

    @staticmethod
    def delete_team(
        db: Session, 
        team_id: int,
        current_user_id: int
    ) -> None:
        """删除团队"""
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        # 检查团队是否有成员
        member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
        if member_count > 0:
            raise HTTPException(status_code=400, detail="团队还有成员，不能删除")
        
        # 检查是否有关联的台账
        ledgers = db.query(models.Ledger).filter(models.Ledger.team_id == team.id).count()
        if ledgers > 0:
            raise HTTPException(status_code=400, detail="该团队已被台账使用，无法删除")
        
        # 删除团队
        db.delete(team)
        db.commit()

    @staticmethod
    def get_team_members(db: Session, team_id: int) -> List[models.User]:
        """获取团队成员列表"""
        try:
            team = db.query(models.Team).filter(models.Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="团队不存在")
            
            members = db.query(models.User).filter(models.User.team_id == team.id).all()
            return members
        except Exception as e:
            print(f"获取团队成员失败: {str(e)}")
            # 返回空列表，而不是抛出错误
            return []

    @staticmethod
    def add_user_to_team(
        db: Session, 
        team_id: int, 
        user_id: int,
        current_user_id: int
    ) -> None:
        """
        将用户添加到团队
        """
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查用户是否已经在团队中
        if user.team_id == team_id:
            raise HTTPException(status_code=400, detail="用户已经在团队中")

        # 决策 1: 调入新组前, 原组的组长位若挂着他要清掉 (组长位不能指向外组的人)
        TeamService.release_leadership_if_left(db, user, user.team_id)

        # G7 组员调换历史: 在改 team_id 之前 (处理器从 user.team_id 现读原组)。
        # 放在上面那个 400 之后 —— 同组重复加入不应该留下历史记录。
        # Phase 4: 局部 import 反向依赖已改为中性事件 (portrait 侧自注册处理器)
        domain_events.dispatch(
            domain_events.EVENT_USER_TEAM_CHANGED,
            db, user=user, to_team_id=team_id, operator_user_id=current_user_id,
        )

        # 添加用户到团队
        user.team_id = team_id
        db.add(user)
        db.commit()

    @staticmethod
    def remove_user_from_team(
        db: Session, 
        team_id: int, 
        user_id: int,
        current_user_id: int
    ) -> None:
        """
        从团队中移除用户
        """
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查用户是否在团队中
        if user.team_id != team_id:
            raise HTTPException(status_code=400, detail="用户不在团队中")

        # 决策 1: 退组 → 若他是本组组长, 本组组长位清空 (组长位不能指向已退组的人)
        TeamService.release_leadership_if_left(db, user, team_id)

        # G7 组员调换历史: to_team_id=None → 记录 to_group="未分组" (Phase 4: 事件化)
        domain_events.dispatch(
            domain_events.EVENT_USER_TEAM_CHANGED,
            db, user=user, to_team_id=None, operator_user_id=current_user_id,
        )

        # 从团队中移除用户
        user.team_id = None
        db.add(user)
        db.commit()


team_service = TeamService() 