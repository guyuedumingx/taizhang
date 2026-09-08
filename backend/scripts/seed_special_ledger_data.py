"""
制造「特殊业务台账」测试数据：一个专用模板 + 覆盖全部乱填模式的台账。

数据写入 dev 库（backend/taizhang.db），用于测试统计分析的清洗层：
- 干净值 / 千分位 / 货币符 / 单位词 / 修饰词 / 语义空值 / 全角
- 会计负数 / 多值范围 / 大写金额 / 越界 / 无法解析
全部写入原始脏值，统计时由 field_normalizers.json 配置的规则链动态清洗。

运行（backend 目录下）: ./venv/bin/python scripts/seed_special_ledger_data.py
可重复执行：先清理同名模板下 TSB2026 前缀的旧数据再重建。
"""
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app import models
from app.services.ledger_service import LedgerService

TEMPLATE_NAME = "特殊业务台账"
SERIAL_PREFIX = "TSB2026"

FIELDS = [
    {"name": "流水号", "label": "流水号", "type": "input", "required": True, "order": 1},
    {"name": "交易码", "label": "交易码", "type": "select", "required": True, "order": 2,
     "options": ["转账", "汇款", "缴费", "退汇"]},
    {"name": "金额", "label": "金额", "type": "number", "required": True, "order": 3},
    {"name": "柜员号", "label": "柜员号", "type": "input", "required": False, "order": 4},
    {"name": "组别", "label": "组别", "type": "input", "required": False, "order": 5},
    {"name": "业务日期", "label": "业务日期", "type": "date", "required": False, "order": 6},
    {"name": "摘要", "label": "摘要", "type": "textarea", "required": False, "order": 7},
]

# (金额原始值, 模式标签) —— 覆盖《特殊栏位处理与填写格式提示方案》3.1 全部乱填模式
AMOUNT_PATTERNS = [
    ("12345.67", "干净"),
    ("8900", "干净"),
    ("1,234,567", "千分位"),
    ("9,800.5", "千分位"),
    ("¥1000", "货币符"),
    ("￥2500.50", "货币符"),
    ("3700元", "货币符"),
    ("100万", "单位词"),
    ("3千", "单位词"),
    ("1.5k", "单位词"),
    ("200W", "单位词"),
    ("约5000", "修饰词"),
    ("5000左右", "修饰词"),
    ("无", "语义空值"),
    ("没有", "语义空值"),
    ("１２３４５", "全角"),
    (" 500 ", "空白"),
    ("(500)", "会计负数"),
    ("100-200", "范围(可疑)"),
    ("500或600", "多值(可疑)"),
    ("人民币叁仟柒佰元整", "大写金额"),
    ("壹万贰仟叁佰肆拾伍元陆角柒分", "大写金额"),
    ("拾伍元", "大写金额"),
    ("壹佰零伍元", "大写金额"),
    ("柒角伍分", "大写金额"),
    ("壹亿零贰拾万", "大写金额"),
    ("999999999", "越界(可疑)"),
    ("见附件", "无法解析(可疑)"),
]

TEAMS = ["城东支行", "高新支行"]
TRADE_CODES = ["转账", "汇款", "缴费", "退汇"]


def ensure_teams(db):
    team_ids = {}
    for name in TEAMS:
        team = db.query(models.Team).filter(models.Team.name == name).first()
        if not team:
            team = models.Team(name=name, department="特殊业务")
            db.add(team)
            db.flush()
        team_ids[name] = team.id
    db.commit()
    return team_ids


def ensure_template(db) -> models.Template:
    template = db.query(models.Template).filter(models.Template.name == TEMPLATE_NAME).first()
    if template:
        # 补齐缺失字段
        existing = {f.name for f in db.query(models.Field).filter(models.Field.template_id == template.id).all()}
        for spec in FIELDS:
            if spec["name"] not in existing:
                db.add(models.Field(template_id=template.id, **spec))
        db.commit()
        return template

    template = models.Template(
        name=TEMPLATE_NAME,
        description="用于验证统计清洗层的测试模板（含大量乱填金额数据）",
        department="特殊业务",
        created_by_id=1,
        updated_by_id=1,
    )
    db.add(template)
    db.flush()
    for spec in FIELDS:
        db.add(models.Field(template_id=template.id, **spec))
    db.commit()
    return template


def clean_old_data(db, template_id):
    old = db.query(models.Ledger).filter(
        models.Ledger.template_id == template_id,
        models.Ledger.name.like(f"{SERIAL_PREFIX}%"),
    ).all()
    for led in old:
        db.delete(led)
    db.commit()
    return len(old)


def seed():
    db = SessionLocal()
    try:
        team_ids = ensure_teams(db)
        template = ensure_template(db)
        removed = clean_old_data(db, template.id)

        random.seed(2026)  # 固定随机种子，数据可复现
        base = datetime.now() - timedelta(days=30)
        created = 0
        pattern_summary: dict = {}

        for i, (amount, tag) in enumerate(AMOUNT_PATTERNS):
            for team_name in TEAMS:
                serial = f"{SERIAL_PREFIX}{i + 1:04d}{team_ids[team_name]}"
                biz_date = base + timedelta(days=random.randint(0, 30))
                data = {
                    "流水号": serial,
                    "交易码": random.choice(TRADE_CODES),
                    "金额": amount,
                    "柜员号": f"E{random.randint(1001, 1099)}",
                    "组别": team_name,
                    "业务日期": biz_date.strftime("%Y-%m-%d"),
                    "摘要": f"{tag}模式测试数据",
                }
                created_at = biz_date + timedelta(hours=random.randint(8, 18))
                ledger = models.Ledger(
                    name=serial,
                    description=f"{TEMPLATE_NAME}-{tag}",
                    status="active",
                    approval_status="approved",
                    template_id=template.id,
                    team_id=team_ids[team_name],
                    created_by_id=1,
                    updated_by_id=1,
                    data=data,
                    created_at=created_at,
                    updated_at=created_at,
                    submitted_at=created_at,
                    approved_at=created_at,
                )
                db.add(ledger)
                db.flush()
                LedgerService.sync_field_values_with_ledger_data(db, ledger.id)
                created += 1
                pattern_summary[tag] = pattern_summary.get(tag, 0) + 1

        db.commit()

        print(f"模板: {TEMPLATE_NAME} (id={template.id})")
        print(f"清理旧数据: {removed} 条")
        print(f"新建台账: {created} 条（{len(TEAMS)} 个团队 × {len(AMOUNT_PATTERNS)} 种金额模式）")
        print("模式分布:")
        for tag, count in sorted(pattern_summary.items(), key=lambda kv: -kv[1]):
            print(f"  {tag}: {count} 条")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
