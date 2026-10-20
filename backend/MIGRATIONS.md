# 迁移脚本执行指南（MIGRATIONS.md）

> 重构方案 Phase 1.5 产物。本文档回答两个问题：**新环境从零部署跑什么**、
> **存量库升级按什么顺序跑什么**。此前 14 个脚本的顺序只存在于 git log 里。

## 一、现状盘点

| 脚本 | 位置 | 幂等 | DB 连接 | 说明 |
|---|---|---|---|---|
| `init_db.py` | backend/ | ✅ | SessionLocal（跟随 settings） | 建 15 张台账表 + Casbin 种子 + admin。**不建任何 portrait 表** |
| `init_portrait_workflows.py` | backend/ | ✅（按名查重） | SessionLocal | 建 4 套画像审批模板。**副作用：import portrait models 后 create_all，是唯一建出全部 28 张 portrait 表的入口** |
| `migrate_pbkdf2_hash.py` | backend/ | ✅（按 `$2x$` 前缀） | SessionLocal | 存量 bcrypt → PBKDF2；**临时密码 = EHR 号，跑完务必通知全员改密**（配合 Phase 0 的服务端强制改密） |
| `migrate_portrait_p1.py` | backend/ | ✅ | SessionLocal | portrait 基础表补齐 |
| `migrate_portrait_c1.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | C1 家访扫描件字段 |
| `migrate_portrait_p6.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | P6 家访端点改造配套 |
| `migrate_portrait_p8.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | P8 submission 联动字段 |
| `migrate_portrait_privacy_remove.py` | backend/ | ✅（跑前自动备份） | **硬编码 `taizhang.db`** | 隐私字段裁剪 |
| `migrate_portrait_skill_tag_created_at.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | 标签表时间列 |
| `migrate_portrait_entry_exit_seq.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | 出入境序号列 |
| `migrate_portrait_activity_record.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | 活动记录表 |
| `migrate_portrait_v21_subtables.py` | backend/ | ✅ | **硬编码 `taizhang.db`** | v2.1 子表（兴趣/获奖等） |
| `migrate_group_transfer_team_ids.py` | backend/ | ✅ | SessionLocal | 组转移历史 team_id 回填 |
| `migrate_home_visit_scan_status.py` | app/db/ | ✅ | engine（settings） | 家访扫描状态列 |
| `migrate_project_summary_completion.py` | app/db/ | ✅ | engine（settings） | 项目总结完成状态列 |

## 二、新环境从零部署

```bash
cd backend
python init_db.py                      # 1. 台账表 + Casbin + admin
python init_portrait_workflows.py      # 2. 28 张 portrait 表 + 4 套审批模板（必跑，别被名字骗了）
# 3. migrate_pbkdf2_hash.py 仅存量 bcrypt 用户环境需要，全新库无需
# 4. 其余 migrate_* 在全新库上均为幂等 no-op，可不跑
```

⚠️ 两个已知坑：
- `migrate_group_transfer_team_ids.py` 在表缺失时报"请先运行 init_db.py 建表"——
  按提示跑 init_db.py **建不出 portrait 表**（它只建台账表），应先跑
  `init_portrait_workflows.py`。
- 8 个硬编码 `taizhang.db` 的脚本：DB 不在默认路径（或 Oracle）时会静默操作
  错误目标/报 no such table。部署 DB 非默认路径时**不要跑它们**，等 Phase 5
  迁移基础设施统一（见重构方案）。

## 三、存量库升级

按**提交顺序**跑（哪个发布带了哪个脚本，翻对应 git log；下表是本分支引入的完整清单）：

```bash
migrate_portrait_p1.py → migrate_portrait_c1.py → migrate_portrait_p6.py →
migrate_portrait_p8.py → migrate_portrait_skill_tag_created_at.py →
migrate_portrait_entry_exit_seq.py → migrate_portrait_privacy_remove.py →
migrate_portrait_activity_record.py → migrate_portrait_v21_subtables.py →
migrate_group_transfer_team_ids.py →（app/db/ 下两个）→ migrate_pbkdf2_hash.py
```

全部支持 `--dry-run`，先 dry-run 看输出再真跑。

## 四、欠账登记（Phase 5 处理）

- 启用 alembic（依赖已在 requirements.txt），当前 schema 做 baseline；
- 14 个脚本归档 `legacy/`，本文档冻结对应关系；
- 统一脚本 DB 连接（全部走 SessionLocal），消除 8 处硬编码路径。
