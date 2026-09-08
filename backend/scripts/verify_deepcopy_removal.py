"""
deepcopy 移除安全性验证脚本（在数据库副本上运行，绝不碰真实库）。

背景：get_ledgers 中的 copy.deepcopy 是历史上为防"会话内实例被意外提交"加的。
事故场景：ORM 实例挂在会话上 → 修改其 JSON 列 → 同会话后续任何一次 commit
（日志/审计等）都会把变更 flush 进库 → 数据污染/报错回滚。

本脚本原样复现该事故并断言不发生，同时验证移除 deepcopy 后的另外两个风险点：
  ① 实例变更 + 强制 commit 后，数据库无任何写入（会话污染）
  ② 响应可正常序列化（expunge 脱离会话后无 DetachedInstanceError）
  ③ 连续两次查询的响应完全一致

用法（backend 目录下）:
  ./venv/bin/python scripts/verify_deepcopy_removal.py

流程:
  1. 对当前代码（含 deepcopy）跑一遍 → 应 PASS，这是基线
  2. 应用改动：把 ledger_service.py 中 `ledgers = copy.deepcopy(ledgers)`
     替换为 `db.expunge_all()`
  3. 再跑一遍 → 仍 PASS 才算验证通过；任何 FAIL 都不要移除 deepcopy
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "taizhang.db")


def table_digest(db) -> str:
    """ledgers 表内容摘要（含 data JSON），任何一行变化都会改变哈希。"""
    rows = db.query(
        models.Ledger.id, models.Ledger.name, models.Ledger.description,
        models.Ledger.status, models.Ledger.approval_status, models.Ledger.data,
    ).order_by(models.Ledger.id).all()
    payload = json.dumps([list(r) for r in rows], ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def serialize(ledgers) -> str:
    """模拟 FastAPI 返回前的序列化（DetachedInstanceError 会在这里暴露）。"""
    return json.dumps(jsonable_encoder(ledgers), ensure_ascii=False, sort_keys=True, default=str)


def main() -> int:
    if not os.path.exists(REAL_DB):
        print(f"未找到开发库: {REAL_DB}")
        return 1

    tmp = tempfile.mktemp(suffix="_verify.db")
    shutil.copy(REAL_DB, tmp)
    print(f"使用数据库副本: {tmp}\n")

    engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    failures = []

    try:
        digest_before = table_digest(db)

        user = db.query(models.User).filter_by(is_superuser=True).first()
        ledgers = LedgerService.get_ledgers(db, skip=0, limit=5, current_user=user)
        print(f"[1] get_ledgers 返回 {len(ledgers)} 条")

        # 复现历史事故：修改实例的 JSON 列，再强制 commit（模拟同会话后续日志/审计提交）
        probe_key = "__verify_probe__"
        target = ledgers[0]
        target.data = {**(target.data or {}), probe_key: "should-not-persist"}
        db.commit()

        digest_after = table_digest(db)
        if digest_before == digest_after:
            print("[2] 实例变更 + commit → 数据库无写入 ✓（无会话污染）")
        else:
            failures.append("实例的 data 修改被写入了数据库（会话污染，正是历史事故）")

        # 清掉内存里的探针再序列化，避免响应含探针键干扰下一步比对
        target.data = {k: v for k, v in (target.data or {}).items() if k != probe_key}
        try:
            first_payload = serialize(ledgers)
            print("[3] 响应序列化 ✓（无 DetachedInstanceError）")
        except Exception as e:
            failures.append(f"序列化失败: {type(e).__name__}: {e}")
            first_payload = None

        # 连续两次查询响应一致
        ledgers2 = LedgerService.get_ledgers(db, skip=0, limit=5, current_user=user)
        if first_payload is not None:
            if serialize(ledgers2) == first_payload:
                print("[4] 连续两次查询响应一致 ✓")
            else:
                failures.append("两次查询的响应内容不一致")

        if db.query(models.Ledger).filter(models.Ledger.data.contains(probe_key)).first() is None:
            print("[5] 探针键未落库 ✓")
        else:
            failures.append("探针键出现在数据库中")

        print()
        if failures:
            print("＝＝＝ 验证失败，不要移除 deepcopy ＝＝＝")
            for f in failures:
                print(f"  ✗ {f}")
            return 1
        print("＝＝＝ 全部通过：当前代码状态下副本安全 ＝＝＝")
        return 0
    finally:
        db.close()
        engine.dispose()
        os.remove(tmp)


from app import models  # noqa: E402  (置于路径设置之后)
from app.services.ledger_service import LedgerService  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
