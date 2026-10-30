"""
台账列表性能诊断（只读业务表）：回答「慢是因为 deepcopy，还是数据库/索引也能优化」。

两部分：
  A. 时间分解 —— 对 get_ledgers 的真实调用采样，把每次请求拆成：
       数据库耗时（执行主查询 + 批量取工作流实例/工作流）
       deepcopy 耗时（对同等结果集直接实测 copy.deepcopy，日志未单列此项）
       其他（总耗时 − 前两项，含序列化前的对象处理）
  B. 索引体检 —— 对热点查询用到的每个候选列检查：
       有没有索引（SQLite: sqlite_master+pragma；Oracle: user_ind_columns）
       区分度（行数 / distinct / null 数 / 选择性）
       执行计划走没走索引（SQLite: EXPLAIN QUERY PLAN；Oracle: DBMS_XPLAN）
       → 输出「★ 建议加索引（附 DDL）/ ✓ 已有且被使用 / ⚠ 有索引但没走 / 低区分度收益有限」

用法（backend 目录下）:
  ./venv/bin/python scripts/diagnose_ledgers.py            # 按默认场景诊断
  ./venv/bin/python scripts/diagnose_ledgers.py --iterations 10 --limit 100

说明：Oracle 的 EXPLAIN PLAN 会写 PLAN_TABLE（诊断基础设施，不碰业务数据）。
"""
import argparse
import copy
import logging
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

# —— 索引候选清单：(表, 列, 为什么是热点) ——
# 来源：get_ledgers 的筛选参数、批量关联加载、列表默认排序。
CANDIDATES = [
    ("ledgers", "template_id",   "列表筛选 template_id / 统计分组"),
    ("ledgers", "team_id",       "列表筛选 team_id / 权限过滤"),
    ("ledgers", "created_by_id", "我的台账（按创建人过滤）"),
    ("ledgers", "status",        "列表筛选 status（不在 7 个性能索引里）"),
    ("ledgers", "approval_status", "列表筛选 approval_status（不在 7 个性能索引里）"),
    ("ledgers", "created_at",    "列表默认排序"),
    ("ledgers", "name",          "关键词搜索（注意 LIKE '%x%' 前导通配走不了 B-tree 索引）"),
    ("fields", "template_id",    "模板字段批量加载"),
    ("field_values", "ledger_id", "行详情/字段值双写"),
    ("field_values", "field_id",  "字段值查询/统计"),
    ("workflow_instances", "ledger_id", "列表批量取工作流实例（unique 约束应隐式带索引，验证存在性）"),
]

PROBE_SQL = {
    ("ledgers", "template_id"):     "SELECT * FROM ledgers WHERE template_id = 1",
    ("ledgers", "team_id"):         "SELECT * FROM ledgers WHERE team_id = 1",
    ("ledgers", "created_by_id"):   "SELECT * FROM ledgers WHERE created_by_id = 1",
    ("ledgers", "status"):          "SELECT * FROM ledgers WHERE status = 'active'",
    ("ledgers", "approval_status"): "SELECT * FROM ledgers WHERE approval_status = 'approved'",
    ("ledgers", "created_at"):      "SELECT * FROM ledgers ORDER BY created_at DESC",
    ("ledgers", "name"):            "SELECT * FROM ledgers WHERE name LIKE '%台账%'",
    ("fields", "template_id"):      "SELECT * FROM fields WHERE template_id = 1",
    ("field_values", "ledger_id"):  "SELECT * FROM field_values WHERE ledger_id = 1",
    ("field_values", "field_id"):   "SELECT * FROM field_values WHERE field_id = 1",
    ("workflow_instances", "ledger_id"): "SELECT * FROM workflow_instances WHERE ledger_id = 1",
}


class StepLogCapture(logging.Handler):
    """收集 taizhang.performance 的步骤日志，解析成 {步骤名: ms}。"""

    def __init__(self):
        super().__init__()
        self.steps, self.totals = [], []

    def emit(self, record):
        msg = record.getMessage()
        if "[台账列表性能分析]" not in msg:  # 排除「工作流实例批量加载」等其他步骤日志
            return
        m = re.search(r"各步骤耗时\(ms\): (.+)", msg)
        if m:
            self.steps.append({
                k: float(v) for k, v in (pair.split("=") for pair in m.group(1).split(", "))
            })
            return
        m = re.search(r"总耗时=([\d.]+)ms", msg)
        if m:
            self.totals.append(float(m.group(1)))


def time_get_ledgers(db_factory, user, filters, limit, warmup, iterations):
    """返回 (各步均值, 总耗时均值, deepcopy均值, 端到端均值)。"""
    capture = StepLogCapture()
    perf_logger = logging.getLogger("taizhang.performance")
    perf_logger.addHandler(capture)

    deepcopy_ms, wall_ms = [], []
    n_steps = n_total_before = 0
    try:
        for i in range(warmup + iterations):
            db = db_factory()
            try:
                t0 = time.perf_counter()
                ledgers = LedgerService.get_ledgers(
                    db, skip=0, limit=limit, current_user=user, **filters)
                wall = (time.perf_counter() - t0) * 1000
                # deepcopy 直接实测：对同等结果集再做一次深拷贝（deepcopy 的副本开销与原件一致）
                t1 = time.perf_counter()
                copy.deepcopy(ledgers)
                d_ms = (time.perf_counter() - t1) * 1000
            finally:
                db.close()
            if i >= warmup:
                wall_ms.append(wall)
                deepcopy_ms.append(d_ms)
    finally:
        perf_logger.removeHandler(capture)

    # 只取正式迭代对应的日志（每次调用产生 1 条 steps + 1 条 total）
    steps = capture.steps[warmup:] if len(capture.steps) > warmup else capture.steps
    totals = capture.totals[warmup:] if len(capture.totals) > warmup else capture.totals
    avg_steps = {
        k: statistics.mean(s[k] for s in steps) for k in steps[0]
    } if steps else {}
    return {
        "avg_steps": avg_steps,
        "total_ms": statistics.mean(totals) if totals else statistics.mean(wall_ms),
        "deepcopy_ms": statistics.mean(deepcopy_ms),
        "wall_ms": statistics.mean(wall_ms),
    }


def existing_index(conn, is_oracle, table, column):
    """该列上是否已有索引，返回索引名列表。"""
    if is_oracle:
        rows = conn.execute(text(
            "SELECT index_name FROM user_ind_columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {"t": table.upper(), "c": column.upper()}).fetchall()
        return sorted({r[0] for r in rows})
    rows = conn.execute(text(
        "SELECT DISTINCT s.name FROM sqlite_master s, pragma_index_info(s.name) ii "
        "WHERE s.type = 'index' AND s.tbl_name = :t AND ii.name = :c"
    ), {"t": table, "c": column}).fetchall()
    return sorted({r[0] for r in rows})


def column_stats(conn, table, column):
    rows = conn.execute(text(f"SELECT COUNT(*), COUNT(DISTINCT {column}), COUNT({column}) FROM {table}")).fetchone()
    total, ndv, non_null = rows
    return {"rows": total, "distinct": ndv, "nulls": total - non_null}


def plan_uses_index(conn, is_oracle, sql):
    """执行计划里是否出现索引访问（有索引时的使用性验证）。"""
    if is_oracle:
        conn.execute(text(f"EXPLAIN PLAN FOR {sql}"))
        rows = conn.execute(text(
            "SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC'))")).fetchall()
        plan = "\n".join((r[0] or "") for r in rows)
        return plan.upper(), ("INDEX" in plan.upper() and "TABLE ACCESS FULL" not in plan.upper())
    rows = conn.execute(text(f"EXPLAIN QUERY PLAN {sql}")).fetchall()
    plan = "\n".join(str(r) for r in rows)
    return plan.upper(), "USING INDEX" in plan.upper()


def diagnose_indexes(engine, is_oracle):
    print("\n" + "＝" * 24 + " B. 索引体检 " + "＝" * 24)
    suggestions, unused, low_sel = [], [], []
    with engine.connect() as conn:
        for table, column, why in CANDIDATES:
            try:
                idx = existing_index(conn, is_oracle, table, column)
                st = column_stats(conn, table, column)
            except Exception as e:
                print(f"  ? {table}.{column}: 检查失败 {type(e).__name__}: {e}")
                continue
            sel = (st["distinct"] / st["rows"]) if st["rows"] else 0
            tag = f"{table}.{column}（{why}）"
            if idx:
                _, used = plan_uses_index(conn, is_oracle, PROBE_SQL[(table, column)])
                mark = "✓" if used else "⚠"
                print(f"  {mark} {tag}: 已有索引 {','.join(idx)}，"
                      f"行数={st['rows']} distinct={st['distinct']}，计划{'走索引' if used else '未走索引(小表/统计信息旧)'}")
                if not used:
                    unused.append(f"{table}.{column}")
            elif st["distinct"] <= 1:
                print(f"  – {tag}: 无索引，但 distinct={st['distinct']}（区分度≈0，加了也没用）")
            elif sel < 0.05:
                print(f"  △ {tag}: 无索引，选择性 {sel:.2f} 偏低（等值筛选可用，优化器可能不选）")
                low_sel.append(f"{table}.{column}")
            else:
                ddl = f"CREATE INDEX ix_{table}_{column} ON {table} ({column});"
                print(f"  ★ {tag}: 无索引！行数={st['rows']} distinct={st['distinct']} 选择性={sel:.2f} → 建议加")
                print(f"      {ddl}")
                suggestions.append((f"{table}.{column}", ddl))
    return suggestions, unused, low_sel


def main() -> int:
    parser = argparse.ArgumentParser(description="台账列表性能诊断（只读）")
    parser.add_argument("--limit", type=int, default=100, help="诊断用的分页大小")
    parser.add_argument("--iterations", type=int, default=5, help="每场景正式采样次数")
    parser.add_argument("--warmup", type=int, default=2, help="预热次数")
    args = parser.parse_args()

    from app.db.session import SessionLocal, engine
    from sqlalchemy import func

    is_oracle = settings.DATABASE_TYPE == "oracle"
    target = (f"{settings.ORACLE_USER}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}"
              f"/?service_name={settings.ORACLE_SERVICE}") if is_oracle else f"SQLite ({settings.SQLITE_DATABASE_URI})"
    print(f"目标库: {target}")
    if is_oracle and settings.ORACLE_PASSWORD == "CHANGE_ME":
        print("✗ backend/.env 里 ORACLE_PASSWORD 还是占位值，先填真实连接参数")
        return 2

    print("\n" + "＝" * 24 + " A. get_ledgers 时间分解 " + "＝" * 24)
    probe = SessionLocal()
    user = probe.query(models.User).filter_by(is_superuser=True).first()
    scenarios = [("无过滤", {})]
    row = (probe.query(models.Ledger.template_id, func.count(models.Ledger.id))
           .filter(models.Ledger.template_id.isnot(None))
           .group_by(models.Ledger.template_id)
           .order_by(func.count(models.Ledger.id).desc()).first())
    if row:
        scenarios.append((f"template_id={row[0]}", {"template_id": row[0]}))
    probe.close()

    summary = []
    for name, filters in scenarios:
        r = time_get_ledgers(SessionLocal, user, filters, args.limit, args.warmup, args.iterations)
        if not r["avg_steps"]:
            print("  ⚠ 未捕获到步骤日志（taizhang.performance 需 INFO 级别），数据库部分无法拆分，"
                  "仅报告总耗时与 deepcopy 实测值")
        db_ms = sum(v for k, v in r["avg_steps"].items()
                    if k in ("3_执行主查询", "4_批量获取工作流实例", "5_批量获取工作流"))
        other_ms = r["total_ms"] - db_ms - r["deepcopy_ms"]
        print(f"  [{name} | limit={args.limit}] 总 {r['total_ms']:.1f}ms = "
              f"数据库 {db_ms:.1f} ({db_ms/r['total_ms']*100:.0f}%) + "
              f"deepcopy {r['deepcopy_ms']:.1f} ({r['deepcopy_ms']/r['total_ms']*100:.0f}%) + "
              f"其他 {other_ms:.1f} ({other_ms/r['total_ms']*100:.0f}%)")
        print(f"    步骤明细: " + ", ".join(f"{k}={v:.2f}" for k, v in r["avg_steps"].items()))
        summary.append({"name": name, "db_ms": db_ms, "deepcopy_ms": r["deepcopy_ms"],
                        "total_ms": r["total_ms"]})

    suggestions, unused, low_sel = diagnose_indexes(engine, is_oracle)

    print("\n" + "＝" * 24 + " 诊断结论 " + "＝" * 24)
    avg = lambda k: statistics.mean(s[k] for s in summary)
    db_share = avg("db_ms") / avg("total_ms") * 100
    dc_share = avg("deepcopy_ms") / avg("total_ms") * 100
    print(f"  数据库查询占 {db_share:.0f}%，deepcopy 占 {dc_share:.0f}%")
    if dc_share >= 30:
        print("  → 主要瓶颈是 deepcopy：优先落地 expunge_all 改造（先过 verify_deepcopy_removal 门）")
    elif db_share >= 50:
        print("  → 主要瓶颈在数据库查询：索引建议优先处理（见下方清单）")
    else:
        print("  → 两者占比都不高，瓶颈可能在别处（网络/序列化/前端），看上面步骤明细定位")
    if suggestions:
        print(f"  → 缺索引 {len(suggestions)} 个：")
        for col, ddl in suggestions:
            print(f"      {ddl}   -- {col}")
        print("      （确认后在 add_perf_indexes.py 的 INDEXES 清单里同步，保持脚本幂等交付）")
    if unused:
        print(f"  → 有索引但计划未走：{', '.join(unused)}（小表属正常；Oracle 可先 GATHER_TABLE_STATS）")
    if low_sel:
        print(f"  → 低区分度待观察：{', '.join(low_sel)}")
    if not (suggestions or unused or low_sel):
        print("  → 索引侧无缺口（候选列全部有索引且被计划使用）")
    return 0


from app.core.config import settings  # noqa: E402  (置于路径设置之后)
from app import models  # noqa: E402
from app.services.ledger_service import LedgerService  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
