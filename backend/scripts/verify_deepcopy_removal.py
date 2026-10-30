"""
deepcopy 移除安全性验证脚本。

背景：get_ledgers 中的 copy.deepcopy 是历史上为防"会话内实例被意外提交"加的。
事故场景：ORM 实例挂在会话上 → 修改其 JSON 列 → 同会话后续任何一次 commit
（日志/审计等）都会把变更 flush 进库 → 数据污染/报错回滚。

本脚本原样复现该事故并断言不发生，同时验证移除 deepcopy 后的另外两个风险点：
  ① 实例变更 + 强制 commit 后，数据库无任何写入（会话污染）
  ② 响应可正常序列化（expunge 脱离会话后无 DetachedInstanceError）
  ③ 连续两次查询的响应完全一致

两种运行模式（按 backend/.env 的 DATABASE_TYPE 自动选择）:
  SQLite（默认）: 复制 taizhang.db 到临时副本，在副本上跑，绝不碰真实库
  Oracle:         无法复制文件 → 改用「快照-测试-恢复」闭环：
                  a. 快照 get_ledgers 返回行的 data 列（测试前状态）
                  b. 跑同样的三项断言
                  c. finally 中用【独立会话】把快照写回 + 全表清扫探针键
                  d. 复核恢复结果，恢复失败会大声报错并列出受影响行 id
                  因为存在"改了又恢复"的写入，Oracle 模式必须显式加 --oracle 确认

用法（backend 目录下）:
  ./venv/bin/python scripts/verify_deepcopy_removal.py            # SQLite 副本模式
  ./venv/bin/python scripts/verify_deepcopy_removal.py --oracle   # Oracle 快照恢复模式

流程:
  1. 对当前代码（含 deepcopy）跑一遍 → 应 PASS，这是基线
  2. 应用改动：把 ledger_service.py 中 `ledgers = copy.deepcopy(ledgers)`
     替换为 `db.expunge_all()`
  3. 再跑一遍 → 仍 PASS 才算验证通过；任何 FAIL 都不要移除 deepcopy

注意：Oracle 模式的探针清扫会全表读取 ledgers.data（Python 侧判断，
避免 LIKE 打在 CLOB 上报 ORA-00932），开发库量级没问题，大表会较慢。
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
PROBE_KEY = "__verify_probe__"


def normalize_data(value):
    """读取侧归一化（语义同内网 util text_to_json）：str 尝试解析为 dict，其余原样。"""
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def encode_data(value):
    """写入侧编码（语义同内网 util json_to_text），按模型列类型自动适配：
    JSON 列（本仓库 models/ledger.py）直接传 dict；
    Text/CLOB 列（内网部署，JSON 存文本）序列化为 str，否则 cx_Oracle 报
    NotSupportedError: python value of dict not supported。"""
    from sqlalchemy.types import JSON as SA_JSON
    if isinstance(models.Ledger.__table__.c.data.type, SA_JSON):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def table_digest(db) -> str:
    """ledgers 表内容摘要（含 data JSON），任何一行变化都会改变哈希。"""
    rows = db.query(
        models.Ledger.id, models.Ledger.name, models.Ledger.description,
        models.Ledger.status, models.Ledger.approval_status, models.Ledger.data,
    ).order_by(models.Ledger.id).all()
    payload = json.dumps([list(r) for r in rows], ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def probe_rows(db) -> list:
    """全表找含探针键的行（Python 侧判断，兼容 dict 与 Text 列存 JSON 字符串两种形态）。"""
    return [
        lid for lid, data in db.query(models.Ledger.id, models.Ledger.data).all()
        if isinstance(normalize_data(data), dict) and PROBE_KEY in normalize_data(data)
    ]


def serialize(ledgers) -> str:
    """模拟 FastAPI 返回前的序列化（DetachedInstanceError 会在这里暴露）。"""
    return json.dumps(jsonable_encoder(ledgers), ensure_ascii=False, sort_keys=True, default=str)


def run_assertions(db, digest_fn) -> int:
    """三项断言的主体。digest_fn(db) 返回当前数据快照，供 [2] 前后比对。"""
    failures = []
    digest_before = digest_fn(db)

    user = db.query(models.User).filter_by(is_superuser=True).first()
    ledgers = LedgerService.get_ledgers(db, skip=0, limit=5, current_user=user)
    print(f"[1] get_ledgers 返回 {len(ledgers)} 条")

    # 复现历史事故：修改实例的 JSON 列，再强制 commit（模拟同会话后续日志/审计提交）
    target = ledgers[0]
    target.data = {**(normalize_data(target.data) or {}), PROBE_KEY: "should-not-persist"}
    db.commit()

    if digest_before == digest_fn(db):
        print("[2] 实例变更 + commit → 数据库无写入 ✓（无会话污染）")
    else:
        failures.append("实例的 data 修改被写入了数据库（会话污染，正是历史事故）")

    # 清掉内存里的探针再序列化，避免响应含探针键干扰下一步比对
    target.data = {k: v for k, v in (normalize_data(target.data) or {}).items() if k != PROBE_KEY}
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

    if not probe_rows(db):
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


def run_sqlite() -> int:
    """原有流程：复制 SQLite 文件到临时副本，断言跑在副本上。"""
    if not os.path.exists(REAL_DB):
        print(f"未找到开发库: {REAL_DB}")
        return 1

    tmp = tempfile.mktemp(suffix="_verify.db")
    shutil.copy(REAL_DB, tmp)
    print(f"使用数据库副本: {tmp}\n")

    engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        return run_assertions(db, table_digest)
    finally:
        db.close()
        engine.dispose()
        os.remove(tmp)


def run_oracle() -> int:
    """快照-测试-恢复闭环，跑在 backend/.env 指向的 Oracle 上。"""
    print(f"目标库: {settings.ORACLE_USER}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}"
          f"/?service_name={settings.ORACLE_SERVICE}\n")
    if settings.ORACLE_PASSWORD == "CHANGE_ME":
        print("✗ backend/.env 里 ORACLE_PASSWORD 还是占位值 CHANGE_ME，先填真实连接参数")
        return 2

    db = SessionLocal()
    try:
        # a. 快照：get_ledgers 返回行的 data（此刻尚未做任何变更）
        user = db.query(models.User).filter_by(is_superuser=True).first()
        ledgers = LedgerService.get_ledgers(db, skip=0, limit=5, current_user=user)
        snapshot = {l.id: normalize_data(l.data) for l in ledgers}
        db.expunge_all()
        print(f"已快照 {len(snapshot)} 行 data 列（测试后按此恢复）")
    finally:
        db.close()

    digest_fn = lambda session: _snapshot_digest(session, snapshot)
    result = 1
    db = SessionLocal()
    try:
        result = run_assertions(db, digest_fn)
    finally:
        db.close()
        result = _restore_oracle(snapshot) or result  # 恢复失败(非0)永远向上传递
    return result


def _snapshot_digest(session, snapshot) -> str:
    """按快照行的 id 集重读 data，返回可比对的摘要。"""
    rows = session.query(models.Ledger.id, models.Ledger.data)\
        .filter(models.Ledger.id.in_(list(snapshot.keys()))).all()
    payload = json.dumps([[r[0], normalize_data(r[1])] for r in rows], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def _restore_oracle(snapshot: dict) -> int:
    """独立会话恢复：写回快照 + 全表清扫探针键 + 复核。返回 0=干净。"""
    fix = SessionLocal()
    try:
        changed = 0
        for lid, original in snapshot.items():
            row = fix.get(models.Ledger, lid)
            if row is None:
                print(f"  ! 恢复时找不到行 id={lid}（测试期间被删？）")
                continue
            if normalize_data(row.data) != original:
                row.data = encode_data(original)
                changed += 1
        # 探针清扫兜底：万一污染波及快照之外的行
        for lid, data in fix.query(models.Ledger.id, models.Ledger.data).all():
            normalized = normalize_data(data)
            if isinstance(normalized, dict) and PROBE_KEY in normalized:
                stripped = {k: v for k, v in normalized.items() if k != PROBE_KEY}
                fix.get(models.Ledger, lid).data = encode_data(stripped)
                changed += 1
        fix.commit()
    finally:
        fix.close()

    # 复核：恢复后再读一遍，必须与快照完全一致
    check = SessionLocal()
    try:
        rows = check.query(models.Ledger.id, models.Ledger.data)\
            .filter(models.Ledger.id.in_(list(snapshot.keys()))).all()
        residual = [lid for lid, data in rows if normalize_data(data) != snapshot[lid]]
        leaked = probe_rows(check)
    finally:
        check.close()

    if not residual and not leaked:
        print(f"\n[恢复] 已复核：快照行与探针清扫全部干净（回写 {changed} 处）✓")
        return 0
    print(f"\n！！！恢复不彻底：residual={residual} leaked={leaked} ！！！")
    print("请手工检查上述行的 data 列（探针键名：__verify_probe__）")
    return 3


from app.core.config import settings  # noqa: E402  (置于路径设置之后)
from app.db.session import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.services.ledger_service import LedgerService  # noqa: E402


def main() -> int:
    if settings.DATABASE_TYPE == "oracle":
        if "--oracle" not in sys.argv:
            print("当前 backend/.env 指向 Oracle（无法像 SQLite 那样复制文件跑副本）。")
            print("Oracle 模式会在目标库上「写入探针→跑断言→自动恢复→复核」，")
            print("确认在【开发/测试库】上运行后，显式加参数：")
            print("  ./venv/bin/python scripts/verify_deepcopy_removal.py --oracle")
            return 2
        return run_oracle()
    return run_sqlite()


if __name__ == "__main__":
    sys.exit(main())
