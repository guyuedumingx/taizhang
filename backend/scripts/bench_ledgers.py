"""
get_ledgers 性能对比基准（纯只读，不写任何数据）。

回答的问题：把 ledger_service.py 里的 `ledgers = copy.deepcopy(ledgers)`
换成 `db.expunge_all()` 之后，接口到底快了多少？

两遍法（与 verify_deepcopy_removal.py 的验证流程一致）：
  1) 当前代码（含 deepcopy）上跑一次，打标签存结果
       ./venv/bin/python scripts/bench_ledgers.py --tag baseline
  2) 应用改动：copy.deepcopy(ledgers) → db.expunge_all()
  3) 再跑一次，换标签
       ./venv/bin/python scripts/bench_ledgers.py --tag expunge
  4) 出对比表
       ./venv/bin/python scripts/bench_ledgers.py --compare baseline expunge

口径：
  - 场景矩阵 = 过滤条件（无/模板/团队，按库内真实数据自动挑）× 分页大小（默认 20/50/100）
  - 每场景预热 3 次不计时，正式计时 N 次（默认 10），报告 min/中位数/p95
  - 每次调用独立 Session（等同真实请求的会话生命周期），并附带响应序列化耗时
    —— expunge 版本的 DetachedInstanceError 风险也会在这里顺带暴露
  - deepcopy 成本随数据量增长，库小时收益不明显；生产真实收益看
    taizhang.performance 日志里「5.5_批量深拷贝」每笔请求的毫秒数

注意：两次对比运行之间不要改库内数据，尽量同时段跑，避免把环境抖动算进差异。
目标库由 backend/.env 决定；跑前会打印目标（不含密码）。
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.encoders import jsonable_encoder

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bench_results")


def stats(values):
    s = sorted(values)
    p95 = s[min(len(s) - 1, int(round(0.95 * len(s))) - (0 if len(s) == 1 else 1))]
    return {"min": round(s[0], 3), "median": round(s[len(s) // 2], 3), "p95": round(p95, 3)}


def serialize(ledgers) -> float:
    """响应序列化（FastAPI 返回前真实会发生），返回耗时 ms。"""
    t0 = time.perf_counter()
    json.dumps(jsonable_encoder(ledgers), ensure_ascii=False, default=str)
    return (time.perf_counter() - t0) * 1000


def pick_scenarios(db):
    """按库内真实数据挑过滤条件：无过滤 + 数据量最多的模板/团队。"""
    from sqlalchemy import func

    scenarios = [("无过滤", {})]
    row = (
        db.query(models.Ledger.template_id, func.count(models.Ledger.id))
        .filter(models.Ledger.template_id.isnot(None))
        .group_by(models.Ledger.template_id)
        .order_by(func.count(models.Ledger.id).desc())
        .first()
    )
    if row:
        scenarios.append((f"模板过滤(template_id={row[0]}, {row[1]}条)", {"template_id": row[0]}))
    row = (
        db.query(models.Ledger.team_id, func.count(models.Ledger.id))
        .filter(models.Ledger.team_id.isnot(None))
        .group_by(models.Ledger.team_id)
        .order_by(func.count(models.Ledger.id).desc())
        .first()
    )
    if row:
        scenarios.append((f"团队过滤(team_id={row[0]}, {row[1]}条)", {"team_id": row[0]}))
    return scenarios


def db_profile(db):
    """数据规模上下文（deepcopy 成本随行数与 JSON 大小增长，对比时要带着看）。"""
    from sqlalchemy import text

    ledgers_cnt = db.execute(text("SELECT COUNT(*) FROM ledgers")).scalar()
    try:
        avg_len = round(db.execute(text("SELECT AVG(LENGTH(data)) FROM ledgers")).scalar() or 0)
    except Exception:
        avg_len = -1  # 个别版本 CLOB 不支持 LENGTH 时降级
    fv_cnt = db.execute(text("SELECT COUNT(*) FROM field_values")).scalar()
    return {"ledgers_rows": ledgers_cnt, "ledgers_data_avg_chars": avg_len, "field_values_rows": fv_cnt}


def run_bench(args) -> int:
    from app.db.session import SessionLocal

    print(f"目标库: {settings.ORACLE_USER}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}"
          f"/?service_name={settings.ORACLE_SERVICE}"
          if settings.DATABASE_TYPE == "oracle" else f"SQLite ({settings.SQLITE_DATABASE_URI})")
    if settings.DATABASE_TYPE == "oracle" and settings.ORACLE_PASSWORD == "CHANGE_ME":
        print("✗ backend/.env 里 ORACLE_PASSWORD 还是占位值，先填真实连接参数")
        return 2

    limits = [int(x) for x in args.limits.split(",")]
    probe = SessionLocal()
    user = probe.query(models.User).filter_by(is_superuser=True).first()
    scenarios = pick_scenarios(probe)
    profile = db_profile(probe)
    probe.close()
    print(f"数据规模: ledgers={profile['ledgers_rows']} 行（data 平均 "
          f"{profile['ledgers_data_avg_chars']} 字符）, field_values={profile['field_values_rows']} 行")
    print(f"场景 {len(scenarios)} 个 × 分页 {limits} × 预热 {args.warmup} + 计时 {args.iterations} 次\n")

    results = {"tag": args.tag, "limits": limits, "iterations": args.iterations,
               "warmup": args.warmup, "profile": profile, "cases": {}}
    for name, filters in scenarios:
        for limit in limits:
            key = f"{name} | limit={limit}"
            gets, sers = [], []
            for i in range(args.warmup + args.iterations):
                db = SessionLocal()
                try:
                    t0 = time.perf_counter()
                    ledgers = LedgerService.get_ledgers(
                        db, skip=0, limit=limit, current_user=user, **filters)
                    t1 = time.perf_counter()
                    ser_ms = serialize(ledgers)
                finally:
                    db.close()
                if i >= args.warmup:
                    gets.append((t1 - t0) * 1000)
                    sers.append(ser_ms)
            results["cases"][key] = {"get_ledgers_ms": stats(gets), "serialize_ms": stats(sers)}
            print(f"  {key}: get_ledgers 中位数 {stats(gets)['median']}ms "
                  f"(p95 {stats(gets)['p95']}ms), 序列化中位数 {stats(sers)['median']}ms")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, f"{args.tag}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已存: {out}")
    print("应用改动后（deepcopy → expunge_all）换 --tag 再跑，然后 --compare 对比。")
    return 0


def compare(args) -> int:
    base_tag, new_tag = args.compare
    base = json.load(open(os.path.join(RESULTS_DIR, f"{base_tag}.json"), encoding="utf-8"))
    new = json.load(open(os.path.join(RESULTS_DIR, f"{new_tag}.json"), encoding="utf-8"))
    print(f"对比: {base_tag} → {new_tag}\n")
    print(f"{'场景':<44} {'中位数ms':>16} {'p95ms':>16}  结论")
    improves = 0
    for key, base_case in base["cases"].items():
        new_case = new["cases"].get(key)
        if not new_case:
            continue
        b, n = base_case["get_ledgers_ms"], new_case["get_ledgers_ms"]
        delta = (n["median"] - b["median"]) / b["median"] * 100 if b["median"] else 0
        verdict = "更快 ✓" if n["median"] < b["median"] else "更慢 ✗"
        improves += 1 if n["median"] < b["median"] else 0
        print(f"{key:<44} {b['median']:>7} → {n['median']:<7} {b['p95']:>7} → {n['p95']:<7}  "
              f"{verdict} ({delta:+.1f}%)")
    total = len(base["cases"])
    print(f"\n汇总: {improves}/{total} 个场景变快。看中位数/p95 的绝对差值——"
          f"注意当前库 ledgers={base['profile']['ledgers_rows']} 行，"
          f"数据越大 deepcopy 省得越多，生产真实收益以 taizhang.performance 日志为准。")
    return 0


from app.core.config import settings  # noqa: E402  (置于路径设置之后)
from app import models  # noqa: E402
from app.services.ledger_service import LedgerService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="get_ledgers 性能对比基准（只读）")
    parser.add_argument("--tag", help="本次运行的结果标签，如 baseline / expunge")
    parser.add_argument("--compare", nargs=2, metavar=("BASE", "NEW"), help="对比两次已存结果")
    parser.add_argument("--limits", default="20,50,100", help="分页大小列表，逗号分隔")
    parser.add_argument("--iterations", type=int, default=10, help="每场景正式计时次数")
    parser.add_argument("--warmup", type=int, default=3, help="每场景预热次数（不计时）")
    args = parser.parse_args()
    if args.compare:
        return compare(args)
    if not args.tag:
        parser.error("请给 --tag（或用 --compare base new 对比已有结果）")
    return run_bench(args)


if __name__ == "__main__":
    sys.exit(main())
