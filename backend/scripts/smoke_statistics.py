"""
特殊台账统计功能全量冒烟测试（在数据库副本上运行，绝不碰真实库）。

覆盖矩阵：
  T1  多模板/全部查询        T2  关键词搜索          T3  系统字段筛选（状态/审批/团队/创建人/时间）
  T4  字段级筛选（含清洗联动）T5  清洗规则归一化       T6  质量报告（有效/清洗/可疑口径）
  T7  动态统计指标（6 种）    T8  排序（系统列+字段列） T9  分页
  T10 Excel 导出（字段列+可疑 Sheet）                 T11 query-fields 元信息
  T12 权限门控（statistics:view）

用法（backend 目录下）: ./venv/bin/python scripts/smoke_statistics.py
预期基线：开发库含 seed 脚本的 56 条特殊业务台账（28 模式 × 2 团队）；
脚本另注入 2 条外币台账（$1000 / 1000美元）用于币种排除验证。
"""
import datetime as dt
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.session as sess
from app import models
from app.schemas.statistics_query import AggregationSpec, FieldFilterCondition, StatisticsQueryRequest
from app.services.casbin_service import check_permission
from app.services.ledger_service import LedgerService
from app.services.statistics_service import StatisticsService

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'✓' if cond else '✗'} {name}{('  [' + detail + ']') if (detail and not cond) else ''}")


def make_q(**kw):
    return StatisticsQueryRequest(**{"system_filters": {}, "page": 1, "page_size": 20, **kw})


def add_fx_ledgers(db, tpl, team_id):
    """注入两条外币台账（历史缺陷下会被错误计入 RMB 汇总）。

    先清理副本中历史冒烟残留的 FX 台账，保证基线确定性。
    """
    for old in db.query(models.Ledger).filter(models.Ledger.name.like("FX2026%")).all():
        db.delete(old)
    db.commit()
    now = dt.datetime.now()
    for i, amt in enumerate(["$1000", "1000美元"], start=1):
        led = models.Ledger(
            name=f"FX2026{i:04d}", description="外币测试", status="active", approval_status="approved",
            template_id=tpl.id, team_id=team_id, created_by_id=1, updated_by_id=1,
            data={"流水号": f"FX2026{i:04d}", "交易码": "转账", "金额": amt, "柜员号": "1000001",
                  "组别": "城东支行", "业务日期": "2026-01-01", "摘要": "外币测试"},
            created_at=now, updated_at=now, submitted_at=now, approved_at=now,
        )
        db.add(led)
        db.flush()
        LedgerService.sync_field_values_with_ledger_data(db, led.id)
    db.commit()


def main():
    tmp = tempfile.mktemp(suffix="_smoke.db")
    shutil.copy(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "taizhang.db"), tmp)
    engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    sess.SessionLocal = sessionmaker(bind=engine)

    try:
        tpl = db.query(models.Template).filter_by(name="特殊业务台账").first()
        team_cd = db.query(models.Team).filter_by(name="城东支行").first()
        add_fx_ledgers(db, tpl, team_cd.id)

        # ---- T1 多模板/全部查询 ----
        print("\n[T1] 基础查询")
        r_all = StatisticsService.query_ledgers(db, make_q())
        check("T1.1 全部模板 total=58", r_all.total == 58, f"got {r_all.total}")
        r_one = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id]))
        check("T1.2 单模板 total=58", r_one.total == 58, f"got {r_one.total}")

        # ---- T2 关键词 ----
        print("[T2] 关键词搜索")
        r_kw = StatisticsService.query_ledgers(db, make_q(keyword="TSB"))
        check("T2.1 keyword=TSB → 56", r_kw.total == 56, f"got {r_kw.total}")
        r_kw2 = StatisticsService.query_ledgers(db, make_q(keyword="外币"))
        check("T2.2 keyword=外币 → 2（匹配描述）", r_kw2.total == 2, f"got {r_kw2.total}")

        # ---- T3 系统字段筛选 ----
        print("[T3] 系统字段筛选")
        from app.schemas.statistics_query import SystemFilters
        r_t = StatisticsService.query_ledgers(db, make_q(system_filters=SystemFilters(team_ids=[team_cd.id])))
        check("T3.1 团队=城东支行 → 30（28 seed + 2 外币）", r_t.total == 30, f"got {r_t.total}")
        r_s = StatisticsService.query_ledgers(db, make_q(system_filters=SystemFilters(approval_status=["rejected"])))
        check("T3.2 审批=rejected → 0", r_s.total == 0, f"got {r_s.total}")
        today = dt.date.today()
        start31 = dt.datetime.combine(today - dt.timedelta(days=31), dt.time.min)
        sql_cnt = db.query(models.Ledger).filter(
            models.Ledger.created_at >= start31).count()
        r_d = StatisticsService.query_ledgers(db, make_q(system_filters=SystemFilters(
            created_at_range=[(today - dt.timedelta(days=31)).isoformat(), today.isoformat()])))
        check(f"T3.3 创建时间近31天 与 SQL 对账（{sql_cnt} 条）", r_d.total == sql_cnt, f"got {r_d.total} vs sql {sql_cnt}")

        # ---- T4 字段级筛选 ----
        print("[T4] 字段级筛选（清洗联动）")
        r_nb = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id],
            field_filters={"金额": FieldFilterCondition(operator="normalized_between", value=[1_000_000, 100_000_000])}))
        check("T4.1 金额∈[1e6,1e9] → 6（外币/可疑排除）", r_nb.total == 6, f"got {r_nb.total}")
        r_eq = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id], field_filters={"交易码": FieldFilterCondition(operator="equals", value="转账")}))
        check("T4.2 交易码=转账（select 精确）≥ 4", r_eq.total >= 4, f"got {r_eq.total}")
        r_ct = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id], field_filters={"摘要": FieldFilterCondition(operator="contains", value="外币")}))
        check("T4.3 摘要 contains 外币 → 2", r_ct.total == 2, f"got {r_ct.total}")

        # ---- T5 清洗归一化抽查 ----
        print("[T5] 清洗规则归一化")
        r_tag = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], keyword="大写金额"))
        check("T5.1 大写金额模式行（描述匹配）= 12", r_tag.total == 12, f"got {r_tag.total}")
        r_eqn = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id],
            field_filters={"金额": FieldFilterCondition(operator="equals", value=12345.67)}))
        check("T5.2 清洗值 equals 12345.67 → 4（干净 2 + 大写金额清洗后 2）", r_eqn.total == 4, f"got {r_eqn.total}")
        raws = {it.data["金额"] for it in r_eqn.items}
        check("T5.3 落库均为原始值",
              raws == {"12345.67", "壹万贰仟叁佰肆拾伍元陆角柒分"}, str(raws))

        # ---- T6 质量报告 ----
        print("[T6] 质量报告")
        fq = r_all.data_quality.fields[0]
        check("T6.1 SUM=8,632,650.18（外币不计入）", abs(fq.sum - 8632650.18) < 0.01, f"got {fq.sum}")
        check("T6.2 有效=44", fq.numeric_count == 44, f"got {fq.numeric_count}")
        check("T6.3 自动清洗=38", fq.cleaned_count == 38, f"got {fq.cleaned_count}")
        check("T6.4 可疑=14（12 脏值 + 2 外币）", fq.suspicious_count == 14, f"got {fq.suspicious_count}")
        fx = [s for s in fq.suspicious_items if s.ledger_name.startswith("FX")]
        check("T6.5 外币进可疑且原因明确", len(fx) == 2 and all("非人民币" in s.reason for s in fx),
              str([(s.raw, s.reason) for s in fx]))

        # ---- T7 动态统计指标 ----
        print("[T7] 动态统计指标")
        r_agg = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id],
            aggregations=[
                AggregationSpec(type="sum", field="金额"),
                AggregationSpec(type="count", field="金额"),
                AggregationSpec(type="avg", field="金额"),
                AggregationSpec(type="max", field="金额"),
                AggregationSpec(type="min", field="金额"),
                AggregationSpec(type="row_count"),
            ]))
        aggs = {a.type: a for a in r_agg.aggregations}
        check("T7.1 sum", abs(aggs["sum"].value - 8632650.18) < 0.01, f"got {aggs['sum'].value}")
        check("T7.2 count=44", aggs["count"].value == 44, f"got {aggs['count'].value}")
        check("T7.3 avg", abs(aggs["avg"].value - 8632650.18 / 44) < 0.01, f"got {aggs['avg'].value}")
        check("T7.4 max=2,000,000（200W）", aggs["max"].value == 2_000_000, f"got {aggs['max'].value}")
        check("T7.5 min=0（语义空值 无→0）", aggs["min"].value == 0, f"got {aggs['min'].value}")
        check("T7.6 row_count=58", aggs["row_count"].value == 58, f"got {aggs['row_count'].value}")

        # ---- T8 排序 ----
        print("[T8] 排序")
        r_asc = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], sort_by="created_at", sort_order="asc"))
        check("T8.1 created_at 升序首条为最早", r_asc.items[0].created_at <= r_asc.items[-1].created_at)
        r_fa = StatisticsService.query_ledgers(db, make_q(
            template_ids=[tpl.id], sort_by="金额", sort_order="desc", page_size=58))
        check("T8.2 金额降序首条为 200W", r_fa.items[0].data.get("金额") == "200W",
              f"got {r_fa.items[0].data.get('金额')}")
        r_na = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], sort_by="name", sort_order="asc", page_size=58))
        names = [it.name for it in r_na.items]
        check("T8.3 名称升序", names == sorted(names))

        # ---- T9 分页 ----
        print("[T9] 分页")
        r_p1 = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], page=1, page_size=10))
        r_p3 = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], page=3, page_size=10))
        r_p9 = StatisticsService.query_ledgers(db, make_q(template_ids=[tpl.id], page=9, page_size=10))
        check("T9.1 每页 10 条", len(r_p1.items) == 10 and len(r_p3.items) == 10)
        check("T9.2 total 各页一致", r_p1.total == r_p3.total == 58)
        check("T9.3 越界页 items 为空但 total 正常", len(r_p9.items) == 0 and r_p9.total == 58)
        check("T9.4 页间无重叠", {i.id for i in r_p1.items}.isdisjoint({i.id for i in r_p3.items}))

        # ---- T10 导出 ----
        print("[T10] Excel 导出")
        buf, fname, ctype = StatisticsService.export_query_results(db, make_q(template_ids=[tpl.id], page_size=200))
        from openpyxl import load_workbook
        wb = load_workbook(buf)
        check("T10.1 双 Sheet", wb.sheetnames == ["查询结果", "可疑数据"], str(wb.sheetnames))
        ws = wb["查询结果"]
        headers = [c.value for c in ws[1]]
        check("T10.2 单模板含字段列", "流水号" in headers and "金额" in headers, str(headers))
        check("T10.3 数据行数 = 58", ws.max_row == 59, f"got {ws.max_row}")
        ws2 = wb["可疑数据"]
        check("T10.4 可疑 Sheet ≥ 14 行", ws2.max_row >= 15, f"got {ws2.max_row}")
        fx_rows = [r for r in ws2.iter_rows(min_row=2, values_only=True) if (r[2] == "金额" and ("$" in str(r[3]) or "美元" in str(r[3])))]
        check("T10.5 外币行在可疑 Sheet", len(fx_rows) == 2)

        # ---- T11 query-fields ----
        print("[T11] 字段元信息")
        qf = StatisticsService.get_query_fields(db, tpl.id)
        qmap = {f.name: f for f in qf}
        check("T11.1 金额 has_pipeline=True", qmap.get("金额") is not None and qmap["金额"].has_pipeline)
        check("T11.2 流水号 has_pipeline=False", not qmap["流水号"].has_pipeline)
        check("T11.3 交易码 options 下拉", qmap["交易码"].options == ["转账", "汇款", "缴费", "退汇"], str(qmap["交易码"].options))

        # ---- T12 权限门控 ----
        print("[T12] 权限门控")
        noperm = db.query(models.User).filter(models.User.is_superuser == False).first()  # noqa: E712
        if noperm is None:
            noperm = models.User(username="noperm_smoke", ehr_id="9999999", name="无权限",
                                 hashed_password="x", is_active=True, is_superuser=False)
            db.add(noperm)
            db.commit()
        check("T12.1 无角色用户 statistics:view=False", not check_permission(str(noperm.id), "statistics", "view"))
        # 超管走 is_superuser 旁路（deps.check_permissions），不依赖 casbin 策略
        from app.api import deps
        check("T12.2 超管旁路放行", deps.check_permissions("statistics", "view", 
              db.query(models.User).filter_by(is_superuser=True).first()))

        # ---- 汇总 ----
        passed = sum(1 for _, ok, _ in RESULTS if ok)
        failed = [n for n, ok, _ in RESULTS if not ok]
        print(f"\n＝＝＝ 冒烟结果: {passed}/{len(RESULTS)} 通过 ＝＝=")
        if failed:
            print("失败项:", "、".join(failed))
            return 1
        print("全部通过 ✓")
        return 0
    finally:
        db.close()
        engine.dispose()
        os.remove(tmp)


if __name__ == "__main__":
    sys.exit(main())
