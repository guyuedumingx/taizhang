"""进程内领域事件注册表 (重构方案 Phase 4)

用途: 核心业务 (user/team) 发生变更时, 扩展模块 (portrait) 需要联动留痕。
此前 team_service / user_service 用**函数内局部 import** 反向调用
`portrait.group_transfer_service.record_transfer` —— 注释自述"避免循环导入
+ 保持分层", 实际只是把循环依赖的报错推迟到运行时, 依赖环本身仍在
(核心层 → 扩展层, 与分层方向相反)。

现在核心层只 dispatch 中性事件名, 扩展层自行注册处理器:
  - 核心层对本模块的依赖是"事件名约定", 不指向任何扩展模块;
  - 扩展模块未注册时 dispatch 是 no-op, 单独部署台账核心时零耦合;
  - 处理器与触发方共用同一个 db 会话, 原子性与原先局部 import 版一致。

与 Phase 2 的 workflow_hooks 同一模式: 注册表本身不认识任何业务。
"""
import logging
from typing import Callable, Dict

from sqlalchemy.orm import Session

logger = logging.getLogger("taizhang.events")

Handler = Callable[..., None]
_handlers: Dict[str, Handler] = {}


def register(event: str, fn: Handler) -> None:
    _handlers[event] = fn


def dispatch(event: str, db: Session, **payload) -> None:
    fn = _handlers.get(event)
    if fn is None:
        return
    try:
        fn(db, **payload)
    except Exception:
        # 留痕失败必须显性暴露 (Rule 12) —— 核心变更与留痕同事务,
        # 抛出即整体回滚, 不产生"组改了但历史没记"的半状态
        logger.exception("领域事件处理器失败 event=%s", event)
        raise


# 事件名约定 (核心层 dispatch 用的字符串在此单点维护)
EVENT_USER_TEAM_CHANGED = "user.team_changed"
