"""
性能工具链测试用例（全部可在本地 SQLite 上跑，不需要真实 Oracle 连接）。

覆盖对象（本轮性能工作交付的 4 个脚本 + 运行配置）：
  verify_deepcopy_removal.py  双模式验证（SQLite 副本 / Oracle 快照恢复、Text 列兼容）
  add_perf_indexes.py         索引幂等执行 + Oracle DDL/EXPLAIN 门
  bench_ledgers.py            基准采样 + 标签对比
  diagnose_ledgers.py         步骤日志解析 + 索引体检
  .vscode/launch.json         一键运行配置完整性

用例矩阵：
  T01 normalize_data 读取归一化          T02 encode_data 按列类型编码（JSON/Text）
  T03 probe_rows 兼容 str 形态数据       T04 Text 列仿真：污染→恢复闭环（内网事故回归）
  T05 verify SQLite 全流程 5 断言        T06/T07 Oracle 模式安全门（无 --oracle / 占位密码）
  T08 索引脚本 SQLite 幂等              T09 Oracle 默认打印 DBA DDL
  T10 --execute 占位密码拦截             T11 INDEXES/VERIFY_SQL 清单一致性
  T12 bench stats 统计口径               T13 bench 跑一轮 + compare 出表
  T14 步骤日志解析（含工作流日志干扰）    T15 索引存在性/计划判断（SQLite 真库）
  T16 diagnose 全流程三大区块            T17 launch.json 配置完整性（含本套用例入口）

运行（backend 目录下）:
  ./venv/bin/python -m pytest tests/scripts_tests -v
"""
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import JSON as SA_JSON, Text

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(BACKEND_DIR, "scripts")
DEV_DB = os.path.join(BACKEND_DIR, "taizhang.db")


def load_script_module(filename, name):
    """按路径加载 scripts/ 下的脚本为模块（与 pytest 的模块命名空间隔离）。"""
    path = os.path.join(SCRIPTS_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(script, args=(), env_extra=None):
    """以子进程跑脚本（cwd=backend），可注入环境变量覆盖 .env，返回 (退出码, 合并输出)。"""
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script), *args],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


SQLITE_ENV = {"DATABASE_TYPE": "sqlite"}
ORACLE_ENV = {"DATABASE_TYPE": "oracle", "ORACLE_PASSWORD": "CHANGE_ME"}


@pytest.fixture(scope="module")
def verify_mod():
    return load_script_module("verify_deepcopy_removal.py", "verify_mod_for_test")


@pytest.fixture(scope="module")
def bench_mod():
    return load_script_module("bench_ledgers.py", "bench_mod_for_test")


@pytest.fixture(scope="module")
def diagnose_mod():
    return load_script_module("diagnose_ledgers.py", "diagnose_mod_for_test")


@pytest.fixture(scope="module")
def indexes_mod():
    return load_script_module("add_perf_indexes.py", "indexes_mod_for_test")


# ───────────────────────── verify_deepcopy_removal ─────────────────────────

class TestVerifyHelpers:
    def test_T01_normalize_data(self, verify_mod):
        """T01: str(JSON)→dict、非 JSON str 原样、dict 透传、None/空串→None。"""
        n = verify_mod.normalize_data
        assert n('{"a": 1, "b": [2]}') == {"a": 1, "b": [2]}
        assert n("普通文本不是JSON") == "普通文本不是JSON"
        assert n({"a": 1}) == {"a": 1}
        assert n(None) is None
        assert n("") is None

    def test_T02_encode_data_by_column_type(self, verify_mod, monkeypatch):
        """T02: JSON 列传 dict 原样；Text 列（内网形态）序列化为 str；None 安全。"""
        from app import models
        encode = verify_mod.encode_data
        assert isinstance(models.Ledger.__table__.c.data.type, SA_JSON)
        assert encode({"a": 1}) == {"a": 1}          # 本仓库模型：JSON 列
        assert encode(None) is None
        monkeypatch.setattr(models.Ledger.__table__.c.data, "type", Text())
        assert json.loads(encode({"a": 1})) == {"a": 1}  # 内网形态：Text 列 → str
        assert encode(None) is None
        assert encode('{"已是字符串": 1}') == '{"已是字符串": 1}'


class TestVerifyOracleRestore:
    def test_T03_probe_rows_detects_str_form(self, verify_mod):
        """T03: probe_rows 能在 Text 列存 JSON 字符串的行里检出探针。"""
        tmp = tempfile.mktemp(suffix="_t03.db")
        shutil.copy(DEV_DB, tmp)
        engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
        Factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = Factory()
        from app import models
        victim = db.query(models.Ledger).first()
        victim.data = json.dumps({"__verify_probe__": "leaked"}, ensure_ascii=False)
        db.commit()
        assert victim.id in verify_mod.probe_rows(db)
        db.close(); engine.dispose(); os.remove(tmp)

    def test_T04_text_column_restore_closed_loop(self, verify_mod, monkeypatch):
        """T04: 内网形态仿真（Text 列+str 数据）——污染已提交后恢复闭环必须还原。"""
        from app import models
        from app.services.ledger_service import LedgerService
        tmp = tempfile.mktemp(suffix="_t04.db")
        shutil.copy(DEV_DB, tmp)
        engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
        Factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        monkeypatch.setattr(verify_mod, "SessionLocal", Factory)
        monkeypatch.setattr(models.Ledger.__table__.c.data, "type", Text())

        db = Factory()
        user = db.query(models.User).filter_by(is_superuser=True).first()
        ledgers = LedgerService.get_ledgers(db, skip=0, limit=5, current_user=user)
        snapshot = {l.id: verify_mod.normalize_data(l.data) for l in ledgers}
        db.close()

        # 制造最坏情况：探针以 Text 列实际形态（str）落库
        victim_id = next(iter(snapshot))
        db = Factory()
        db.get(models.Ledger, victim_id).data = json.dumps(
            {**(snapshot[victim_id] or {}), verify_mod.PROBE_KEY: "leaked"}, ensure_ascii=False)
        db.commit()
        assert victim_id in verify_mod.probe_rows(db)
        db.close()

        assert verify_mod._restore_oracle(snapshot) == 0

        db = Factory()
        rows = db.query(models.Ledger.id, models.Ledger.data).filter(
            models.Ledger.id.in_(snapshot)).all()
        assert all(verify_mod.normalize_data(d) == snapshot[i] for i, d in rows)
        assert verify_mod.probe_rows(db) == []
        db.close(); engine.dispose(); os.remove(tmp)


class TestVerifyCli:
    def test_T05_sqlite_full_flow(self):
        """T05: SQLite 副本模式全流程，5 项断言全过、退出码 0。"""
        rc, out = run_cli("verify_deepcopy_removal.py", env_extra=SQLITE_ENV)
        assert rc == 0, out
        for marker in ["[1]", "[2]", "[3]", "[4]", "[5]", "全部通过"]:
            assert marker in out

    def test_T06_oracle_requires_flag(self):
        """T06: .env 指向 Oracle 时不带 --oracle 必须拦截（退出码 2 + 指引）。"""
        rc, out = run_cli("verify_deepcopy_removal.py", env_extra=ORACLE_ENV)
        assert rc == 2
        assert "--oracle" in out

    def test_T07_oracle_placeholder_password_blocked(self):
        """T07: --oracle + 占位密码 CHANGE_ME 必须拦在连接之前（退出码 2）。"""
        rc, out = run_cli("verify_deepcopy_removal.py", ["--oracle"], env_extra=ORACLE_ENV)
        assert rc == 2
        assert "CHANGE_ME" in out


# ───────────────────────── add_perf_indexes ─────────────────────────

class TestIndexScript:
    def test_T08_sqlite_idempotent(self):
        """T08: SQLite 幂等——重复执行全部跳过、新建 0、退出码 0。"""
        for _ in range(2):
            rc, out = run_cli("add_perf_indexes.py", env_extra=SQLITE_ENV)
            assert rc == 0, out
            assert "新建 0 个" in out and "跳过 7 个" in out

    def test_T09_oracle_default_prints_dda(self):
        """T09: Oracle 默认模式不连库，打印 7 条 DBA DDL（NOLOGGING ONLINE）。"""
        rc, out = run_cli("add_perf_indexes.py", env_extra={"DATABASE_TYPE": "oracle"})
        assert rc == 0, out
        assert out.count("NOLOGGING ONLINE;") == 7

    def test_T10_execute_placeholder_password_blocked(self):
        """T10: --execute 遇占位密码必须在连接前拦截（退出码 2）。"""
        rc, out = run_cli("add_perf_indexes.py", ["--execute"], env_extra=ORACLE_ENV)
        assert rc == 2
        assert "CHANGE_ME" in out

    def test_T11_indexes_verify_sql_consistency(self, indexes_mod):
        """T11: INDEXES 与 VERIFY_SQL 一一对应（EXPLAIN 验证不漏索引）。"""
        names = {name for name, _, _ in indexes_mod.INDEXES}
        assert names == set(indexes_mod.VERIFY_SQL.keys())
        assert len(indexes_mod.INDEXES) == 7


# ───────────────────────── bench_ledgers ─────────────────────────

class TestBench:
    def test_T12_stats(self, bench_mod):
        """T12: stats 统计口径（min/median/p95 单调、四舍五入）。"""
        s = bench_mod.stats([5.0, 1.0, 3.0, 2.0, 4.0])
        assert s["min"] == 1.0 and s["median"] == 3.0
        assert s["min"] <= s["median"] <= s["p95"]

    def test_T13_run_and_compare_roundtrip(self):
        """T13: 跑一轮（存 JSON 产物）+ compare 自身（出对比表），全链路退出码 0。"""
        rc, out = run_cli("bench_ledgers.py",
                          ["--tag", "_selftest", "--limits", "20", "--iterations", "2", "--warmup", "1"],
                          env_extra=SQLITE_ENV)
        assert rc == 0, out
        result_file = os.path.join(SCRIPTS_DIR, ".bench_results", "_selftest.json")
        assert os.path.exists(result_file)
        data = json.load(open(result_file, encoding="utf-8"))
        assert data["tag"] == "_selftest" and data["cases"]
        first_case = next(iter(data["cases"].values()))
        assert {"get_ledgers_ms", "serialize_ms"} <= set(first_case.keys())

        rc, out = run_cli("bench_ledgers.py", ["--compare", "_selftest", "_selftest"],
                          env_extra=SQLITE_ENV)
        assert rc == 0, out
        assert "对比:" in out and "汇总" in out
        os.remove(result_file)


# ───────────────────────── diagnose_ledgers ─────────────────────────

class TestDiagnose:
    def test_T14_step_log_capture(self, diagnose_mod):
        """T14: 步骤日志解析正确，且忽略「工作流实例批量加载」等其他来源的干扰日志。"""
        capture = diagnose_mod.StepLogCapture()
        decoy = logging.LogRecord("t", logging.INFO, "p", 1,
                                  "[工作流实例批量加载] 各步骤耗时(ms): 1_构建查询=0.04, 2_执行查询=0.11",
                                  None, None)
        steps = logging.LogRecord("t", logging.INFO, "p", 1,
                                  "[台账列表性能分析] 各步骤耗时(ms): 1_构建查询条件=0.02, "
                                  "2_添加预加载选项=0.07, 3_执行主查询=1.29, 4_批量获取工作流实例=0.20, "
                                  "5_批量获取工作流=0.00, 6_设置关联数据=0.01", None, None)
        total = logging.LogRecord("t", logging.INFO, "p", 1,
                                  "[台账列表性能分析] 总耗时=2.12ms, 平均每条=0.42ms", None, None)
        for rec in (decoy, steps, total):
            capture.emit(rec)
        assert len(capture.steps) == 1          # 干扰日志被排除
        assert capture.steps[0]["3_执行主查询"] == pytest.approx(1.29)
        assert capture.totals == [pytest.approx(2.12)]

    def test_T15_existing_index_and_plan(self, diagnose_mod):
        """T15: 索引存在性判断与执行计划判断（真库：template_id 走索引、LIKE 全表扫）。"""
        tmp = tempfile.mktemp(suffix="_t15.db")
        shutil.copy(DEV_DB, tmp)
        engine = create_engine(f"sqlite:///{tmp}?check_same_thread=False")
        with engine.connect() as conn:
            idx = diagnose_mod.existing_index(conn, False, "ledgers", "template_id")
            assert "ix_ledgers_template_id" in idx
            _, used = diagnose_mod.plan_uses_index(
                conn, False, "SELECT * FROM ledgers WHERE template_id = 1")
            assert used is True
            _, used = diagnose_mod.plan_uses_index(
                conn, False, "SELECT * FROM ledgers WHERE name LIKE '%台账%'")
            assert used is False
        engine.dispose(); os.remove(tmp)

    def test_T16_full_run_sections(self):
        """T16: 全流程退出码 0，A 时间分解 / B 索引体检 / 诊断结论 三区块齐全。"""
        rc, out = run_cli("diagnose_ledgers.py",
                          ["--iterations", "1", "--warmup", "1", "--limit", "20"],
                          env_extra=SQLITE_ENV)
        assert rc == 0, out
        for section in ["A. get_ledgers 时间分解", "B. 索引体检", "诊断结论"]:
            assert section in out


# ───────────────────────── launch.json ─────────────────────────

class TestLaunchConfig:
    def test_T17_launch_json_valid(self):
        """T17: 9 个一键配置全部指向真实脚本，inputs 引用完整。"""
        repo_root = os.path.dirname(BACKEND_DIR)
        path = os.path.join(repo_root, ".vscode", "launch.json")
        raw = open(path, encoding="utf-8").read()
        stripped = re.sub(r"^\s*//.*$", "", raw, flags=re.M)
        cfg = json.loads(stripped)
        assert len(cfg["configurations"]) == 10
        input_ids = {i["id"] for i in cfg["inputs"]}
        for c in cfg["configurations"]:
            if "module" in c:  # module 型配置（如 pytest）：验证模块可导入
                assert importlib.util.find_spec(c["module"]) is not None, \
                    f"配置 {c['name']} 的模块不可导入: {c['module']}"
                continue
            program = c.get("program", "").replace("${workspaceFolder}", repo_root)
            assert program and os.path.exists(program), f"配置 {c['name']} 的程序不存在: {program}"
            for arg in c.get("args", []):
                m = re.match(r"\$\{input:(\w+)\}", str(arg))
                if m:
                    assert m.group(1) in input_ids, f"配置 {c['name']} 引用了未定义的 input"
