"""进程内登录失败锁定 (重构方案 Phase 0: 评审 P0-2)

配合迁移脚本把存量密码重置为 EHR 号的现状: EHR 号 7 位数字且全员可见,
若无失败锁定, 暴力猜解成本趋近于零。连续失败 MAX_FAILURES 次后锁定
LOCK_SECONDS, 期间登录直接 429, 不再触达密码验证。

局限 (有意为之的取舍): 状态存进程内存 —— 单进程部署 (本项目 SQLite/
单 uvicorn 的现状) 下有效; 若将来多 worker/多实例部署, 需换共享存储
(Redis 或 DB 表), 届时把本模块的三个方法换成同签名实现即可。
"""
import threading
import time
from typing import Dict

from fastapi import HTTPException

MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60


class LoginThrottle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: Dict[str, Dict] = {}

    def check(self, key: str) -> None:
        """已锁定则抛 429, 未锁定静默放行。登录入口在验密前调用。"""
        with self._lock:
            rec = self._failures.get(key)
            if rec and rec["locked_until"] > time.time():
                wait_min = int((rec["locked_until"] - time.time()) // 60) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"登录失败次数过多, 账号已临时锁定, 请约 {wait_min} 分钟后重试",
                )

    def record_failure(self, key: str) -> None:
        """记一次失败; 达到阈值则锁定并清零计数 (锁定期内不计次)。"""
        with self._lock:
            rec = self._failures.setdefault(key, {"count": 0, "locked_until": 0.0})
            if rec["locked_until"] > time.time():
                return
            rec["count"] += 1
            if rec["count"] >= MAX_FAILURES:
                rec["locked_until"] = time.time() + LOCK_SECONDS
                rec["count"] = 0

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self, key: str) -> None:
        """管理用途: 手动解除某账号锁定。"""
        with self._lock:
            self._failures.pop(key, None)


login_throttle = LoginThrottle()
