from typing import Any, List, Optional, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.utils.logger import LoggerService


class TeamService:
    """团队服务类，处理团队相关的业务逻辑"""

    @staticmethod
    def get_teams(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[models.Team]:
        """获取团队列表"""
        # 构建查询
        query = db.query(models.Team)
        
        # 搜索
        if search:
            query = query.filter(models.Team.name.ilike(f"%{search}%"))
        
        # 分页
        teams = query.offset(skip).limit(limit).all()
        
        # 计算每个团队的成员数量
        for team in teams:
            team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
            
            # 获取团队负责人姓名
            if team.leader_id:
                leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
                team.leader_name = leader.name if leader else None
            else:
                team.leader_name = None
        
        return teams

    @staticmethod
    def create_team(
        db: Session,
        team_in: schemas.TeamCreate,
        current_user_id: int
    ) -> models.Team:
        """创建新团队"""
        # 检查团队名称是否已存在
        team = db.query(models.Team).filter(models.Team.name == team_in.name).first()
        if team:
            raise HTTPException(
                status_code=400,
                detail="团队名称已存在",
            )
        
        # 创建团队
        team = models.Team(
            name=team_in.name,
            description=team_in.description,
            department=team_in.department,
            leader_id=current_user_id,
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        
        return team

    @staticmethod
    def get_team(db: Session, team_id: int) -> models.Team:
        """获取团队详情"""
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="团队不存在")
        
        # 计算成员数量
        team.member_count = db.query(models.User).filter(models.User.team_id == team.id).count()
        
        # 获取团队负责人姓名
        if team.leader_id:
            leader = db.query(models.User).filter(models.User.id == team.leader_id).first()
            team.leader_name = leader.name if leader else None
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
    ) -> models.Team:
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
        
        return team

    @staticmethod
    def get_team_members(db: Session, team_id: int) -> List[Dict[str, Any]]:
        """获取团队成员列表"""
        try:
            team = db.query(models.Team).filter(models.Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="团队不存在")
            
            members = db.query(models.User).filter(models.User.team_id == team.id).all()
            
            # 简化返回，只返回基本信息
            result = []
            for member in members:
                member_data = {
                    "id": member.id,
                    "username": member.username,
                    "name": member.name or "",
                    "department": member.department or "",
                }
                result.append(member_data)
            
            return result
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
    ) -> models.Team:
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
        
        # 添加用户到团队
        user.team_id = team_id
        db.add(user)
        db.commit()
        
        return team

    @staticmethod
    def remove_user_from_team(
        db: Session, 
        team_id: int, 
        user_id: int,
        current_user_id: int
    ) -> models.Team:
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
        
        # 从团队中移除用户
        user.team_id = None
        db.add(user)
        db.commit()
        
        return team


team_service = TeamService() 