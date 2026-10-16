# 数字画像 · PRD 实现差距审计报告

> **审计对象**：`PRD-员工数字画像系统-v2.0.md`（19 章 + 附录，903 行）
> **审计范围**：`backend/app/portrait/` + `backend/app/api/api_v1/endpoints/users.py` + `frontend/src/pages/portrait/`
> **审计日期**：2026-10-14
> **审计方式**：4 个 Explore agent 并行分段核对（§4-6 / §7-9 / §10-12 / §13-18）+ 人工逐行复核
> **性质**：静态代码审计，**未运行任何写操作**，所有结论均带 `文件:行号` 可复查
> **免责**：结论反映审计时点代码状态。PRD 与代码冲突时，以代码为准；PRD 过期需同步修订。

---

## 摘要

| 类别 | 数量 | 说明 |
|---|---:|---|
| ✅ 完全一致 | 6 | §13 权限矩阵 23 行中 6 行一致 |
| 🔴 权限漏洞 | 6 | 均可造成越权读取，非仅功能缺失 |
| ⚠️ 确定 Bug | 5 | 改法唯一、无口径争议 |
| ❌ 功能缺失 | 20+ | 需排期 |
| 🔀 与 PRD 不符 | 12 | 部分是 PRD 过期，部分是实现走偏 |
| ❓ 需业务确认 | 12 | **本报告核心**，含 4 处 PRD 自身自相矛盾 |

**最重要的三条结论**（详见下）：

1. **代码里不存在"组长"这个角色**——它是 `team_id is not None` 的同义词，导致 §13 权限矩阵 15 个 ❌ 的共同根因
2. **消防演练三个函数把 `viewer` 参数声明了但从未使用**，实际是全表直查
3. **审批人下拉对普通员工恒为空**，B1/B2 两个员工自助功能整体不可用（系收紧 `/users/` 权限时引入的回归）

### 本次已修复（随报告同步交付）

| # | 问题 | 修法 | 验证 |
|---|---|---|---|
| 1.2 | 演练三函数 `viewer` 空转 | 新增 `_visible_drill_ids_subq()` + 三处接上，行集按 §13 收口 | 新增 `test_drill_read_permission_isolated_by_viewer` |
| 1.2.1 | 矩阵藏起零参加者 | 行集改为**基准全员**（§13 范围内全员在职），`total_participants` 单独统计 | `test_drill_baseline` 改写为断言新语义 |
| 1.3 | 家访 `None == None` 空值越权 | 补 `viewer.team_id` 非空守卫 | 复用既有 home_visit 用例 |
| 2.1 | 审批人下拉恒为空（B1/B2 不可用） | 改调 `getUserMembers()`；`catch {}` 改为显性报错 | `tsc --noEmit` |
| 2.2 | `visitor_info` 恒 NULL | 改由**后端** `_build_visitor_info()` 拼装（前端拿不到访人岗位） | 新增 2 个 `visitor_info` 用例 |
| 2.3 | 被访人联系电话无回填源 | 按用户决定改**手填**，不动 P0.1 隐私裁剪 | 表单新增字段 + 编辑回显 |
| 决策项 1 | 演练矩阵无法聚焦 | 行集改「基准全员」+ 加**年份 / 团队筛选器** | 后端 `matrix(year, team_name)` + 前端筛选控件 |
| 3.1 | 家访 F11 批量导入 ❌ | 新增 14 列模板 + `POST /home-visits/import` + `import_rows()` | 新增 `test_home_visit_f11_f12.py`（**15 用例，已全部通过**） |
| 3.2 | 家访 F12 年度矩阵 ❌ | 新增 `GET /home-visits/matrix`，行=员工 / 列=年份 / 单元格=具体日期 | 同上 |
| 3.3 | 家访导出 Excel ❌ | 新增 `GET /home-visits/export`，与模板同 14 列 | 同上 |
| 3.4 | C3 预览打印 / 导出 PDF ❌ | 前端打印预览弹窗（`window.print()`）+ `@media print` 样式 | `tsc --noEmit` |
| 3.5 | C1-7 `scan_status` 模型缺列 | 加列 + 迁移脚本 + 表单必填 + 导出第 14 列 | 迁移脚本已对开发库执行 |
| — | 导���端点越权（本次新引入） | 显式 403 拦普通员工 | `test_export_excel_normal_user_rejected` |

**未修（需业务先拍板）**：决策项 2 / 5 / 6 / 7 及 §三 其余功能缺失项。

> ⚠️ **本次审计发现测试直接写开发库**：`tests/conftest.py:15` 的 `db` fixture 用 `SessionLocal`，指向 `taizhang.db` 而非测试库。测试残留会在开发库累积（本次已清理 7 条演练记录，经用户授权）。**待修，见 §六 6.6。**

---

## 一、权限漏洞（6 条）

### 1.1 「组长」用 `team_id` 非空代替，导致权限整体放宽 🔴

**根因，影响面最大。**

`backend/app/models/user.py:6-27` 的 `User` 表只有 `is_superuser: bool` 和 `team_id: int`，**没有 role / is_leader 字段**。casbin 里虽有 `manager` 角色（`app/db/init_db.py:16-60`），但 portrait 模块**从未引用 casbin**。

所有 portrait 权限判定是手写分支，判据只有三条（`profile_service.py:24-35` 及同构的 7 个 service）：

```python
if viewer.is_superuser: return True                                  # 管理员
if viewer.team_id and viewer.team_id == X.team_id: return True      # ← 这个被当成"组长"
if viewer.id == X.id: return True                                   # 本人
```

即 **"组长" ≡ `team_id is not None`**。而批量导入时组别是常规字段（PRD §16.1 要求"姓名/组别必填"），意味着**任何被分配了组别的普通员工自动获得组长权限**。

真实组长标记其实存在 `Team.leader_id`（`models/team.py:15`），但家访 / 档案 / 演练模块都没用它。

**连带失效**：

| 功能 | PRD §13 要求 | 实际 |
|---|---|---|
| 他人档案查看 | 员工 ❌ | 有组别的员工即可看本组 |
| 档案管理列表 | 员工 ❌ | 同上 |
| 家访新建 | 员工 ❌ | 任何有组别者都能建 |
| 家访列表 | 员工仅自己 | 本组全员可见 |
| 出入境台账 | 员工仅自己 | 本组全员可见 |
| 消防演练（看） | 员工仅自己 | 全员可见（见 1.2） |

> **测试假象**：`test_home_visits.py` 的"普通员工被拒"用例依赖 `normal_user` 的 `team_id=None`，一旦给普通员工分组，该断言即失效。**测试通过不代表权限正确。**

### 1.2 消防演练：`viewer` 参数空转，实际全表直查 🔴

`backend/app/portrait/services/drill_service.py`

`list_records:75` / `get_detail:116` / `matrix:156` 三个函数签名都声明 `viewer: models.User`，router 也传了，**但函数体一次都没引用**。`grep -n viewer` 全文仅 3 个命中，全在签名行。

```python
def matrix(db: Session, *, viewer: models.User) -> DrillMatrix:
    drills = db.query(portrait_models.DrillRecord).order_by(...).all()   # 全表
```

**后果**：任意登录员工可见全部演练记录、全部参与人（含 ehr_id + 姓名）、全公司演练矩阵。违反 §13「员工仅自己」。

> **状态**：✅ 已修复（本次）。新增 `_visible_drill_ids_subq()` helper + 回归测试 `test_drill_read_permission_isolated_by_viewer`。
> **注意**：矩阵**行集**仍由参与记录反推（见 1.2.1），本次只修了列级 + 行集权限收口，**未改行集业务口径**。

#### 1.2.1 矩阵把"零参加者"藏起来了 🔴 业务问题，未修

```python
ehr_set: set[str] = set()
for did in drill_ids:
    ehr_set.update(participation[did].keys())   # ← 只从"参与记录"反推
```

矩阵的行 = **参与过至少一场演练的人**。但 PRD 附录 B.1 写的是「全员 × 全部活动」，§10.2.3 说用途是"一眼看到哪些人/组参与度低"。

**结果与 PRD 意图相反**：全公司一场演练都没参加过的人，根本不在这张表里出现。矩阵退化为"参与者 × 全部活动"的互比，最该被盯住的零参与者被系统自动隐藏。

> **2026-10-14 用户决定**：行集**维持"仅参与者"**，改为加**年份 + 团队筛选器**（`matrix(year=, team_name=)`），靠筛选聚焦而非铺开全员。
>
> ✅ 已实现：`drill_service.matrix()` 加 year/team_name 过滤；`drill.py:56` 端点透传；`DrillsPage.tsx` 加两个筛选下拉（候选项从不筛选的全量矩阵 `matrixAll` 推导，避免"选了年份就看不到其他年份"）。
>
> ⚠️ **该决定未完全消除原问题**：从未参加过任何演练的人仍不出现在矩阵中。筛选器只能定位到"参加过至少一场的人里谁没来某一场"。若后续仍需考核零参加者，须改行集口径（PRD §10.2.3 措辞也需同步修订）。

### 1.3 家访详情 `None == None` 空值越权 🔴 ✅ 已修复

`backend/app/portrait/services/home_visit_service.py:457`

```python
if visited.team_id == viewer.team_id:      # ← None == None 为 True
    return record
if record.visited_user_id == viewer.id:    # ← 真正的本人判定排在之后
    return record
```

`users.team_id` 是 `nullable=True`。两个未分组用户比较结果为真 → **未分组查看者可读任意未分组用户的家访详情**（含被访人电话、地址、反馈）。

同逻辑在 `profile_service.py:30` 写的是 `if viewer.team_id and ...`——守卫是对的，只是没复制到 home_visit。

> **状态**：✅ 已修复，补上 `viewer.team_id` 非空守卫。同文件 `list_visits:394-411` 是 SQL 层判断且已有 `is not None`，无此问题。

### 1.4 `/users/` 曾向任意登录员工吐出全行密码哈希 🔴 ✅ 已修复（2026-10-14）

`backend/app/api/api_v1/endpoints/users.py:19-32`

原 `GET /users/` **无任何权限校验**，且响应模型 `schemas.User` 曾**包含 `hashed_password` 字段**。任意登录员工可拉取全行 1494 人的 PBKDF2 密码哈希 + username，可离线定向爆破。

> **状态**：✅ 已修复——加 `check_permissions("user","view")` 守卫 + 从响应 schema 移除 `hashed_password` + 新建最小集端点 `/users/members`。
> ⚠️ **本次审计发现该修复引入了新回归**，见 2.1。

### 1.5 家访编辑的管理员兜底缺失 ⚠️

`backend/app/portrait/routers/home_visits.py:206`

PRD §13 家访编辑那格写的是「管理员 ❌（**接口兜底 403**）」。代码只判了 `record.visitor_user_id != current_user.id`，**没有任何 admin 拦截**——管理员因为建不了记录（`home_visit_service.py:106-107` 主动禁止）才"碰巧"被挡住，不是设计出来的 403。

→ 属**决策项 2**。

### 1.6 审批工作台的可见范围是"按人"不是"按组" ⚠️

`backend/app/portrait/services/submission_service.py:511-514`

`list_pending_for_user` 严格按 `current_approver_id == viewer.id`，而审批人由**提交人任意指定**（`:81-90` 只校验"存在 + is_active"，**无同组校验**）。

后果：
- 员工可被指定为审批人（PRD §13 说员工 ❌）
- 组长可被指派/审批跨组记录（PRD 说本组）
- 默认审批人取「**第一个** is_superuser」（`:50-57`）→ **多管理员时，其余管理员的"待审批"Tab 永远是空的**

---

## 二、确定 Bug（5 条）

### 2.1 审批人下拉对普通员工恒为空，B1/B2 整体不可用 🔴 ✅ 已修复

**这是收紧 `/users/` 权限（1.4）时引入的回归，写本报告时自查发现。**

`frontend/src/pages/portrait/CreateSubmissionModal.tsx:34` 原调 `listUsersForApprover` → 打 `/users/`，该端点现需 `user:view` 权限，普通员工 → **403**。

三重放大：

1. `next_approver_id` 在 B1/B2 是**必填**（`:100,:194`）
2. `ApproverSelect` 的 `catch {}` **静默吞掉错误**（`:36-38`），UI 无任何提示
3. 上一轮只把 `WorkflowService.ts:42` 和 `HomeVisits.tsx` 切到 `/users/members`，**漏了这个调用点**

**后果**：普通员工无法提交专项工作和活动申报。

> **状态**：✅ 已修复——改调 `getUserMembers()`（`api/users.ts` 的接口注释本就写明"业务选择器统一走这个接口，不要用 getUsers"），`catch {}` 改为 `message.error` 显性报错（Rule 12）。
> ⚠️ **`DrillsPage.tsx:103` 仍在用 `listUsersForApprover`**——当前该页是 admin 专用（`_require_admin`），admin 有权限故不受影响；但若按 §13 放开组长登记演练，**这里会立即炸**。建议在放开前一并切换。

### 2.2 `visitor_info` 恒为 NULL ⚠️ ✅ 已修复

`frontend/src/pages/portrait/CreateHomeVisitModal.tsx:232` 原提交 `visitor_info: allValues.visitor_info`，但 `grep visitor_info` 全文仅此 1 处，两个 Step 都没有 `name="visitor_info"` 的 `Form.Item` → 恒 undefined → DB 列恒 NULL。

**实测阻塞点**：表单字段清单为 `visited_ehr_id / visit_year / visit_method / visit_time / visit_address / co_visitor_user_id / is_visited / file / team_name / visit_date / position / feedback`。

- **主访人无表单字段**——主访人=当前登录用户，服务端隐含设置
- **访人岗位字段完全不存在**——`position` 是**被访人**岗位
- 前端 `coVisitorCandidates` 只有 id/name/ehr_id，主访人连姓名都没有 → **前端无论如何拼不出 B.4 第 10 列**

> **2026-10-14 用户决定**：按 PRD B.4 第 10 列原样，格式 `1.<姓名>，<岗位>`。
>
> ✅ 已实现：改由**后端** `home_visit_service._build_visitor_info()` 拼装（岗位取 `users.department`，与 drill 矩阵 `position` 列同源）。选后端而非前端的原因：前端拿不到访人岗位，且 F11 批量导入路径可复用同一逻辑。
> 同步修了 `co_visitor` 可能未定义的隐患（原代码只在 `if` 块内赋值）。
> 新增 2 个回归用例：双人格式 / 单人不报 NameError。

### 2.3 被家访人联系电话回填无数据源 ⚠️ ✅ 已按用户决定处理

`CreateHomeVisitModal.tsx:137-142` 原只回填岗位，`:234` 注释把 `contact_phone` 与 `mobile/home_phone` 一并列为"已删除"。

但 `HomeVisitRecord.contact_phone` **这列还在**（`log_visit_transfer.py:56`），schema 也接受（`schemas/home_visit.py:27,:61`）。

**关键事实**：`Profile` 全部列无任何电话字段；`ContactInfo` 经 P0.1 裁剪后只剩 `email` + `commute_minutes`。**PRD §7.1 要求的自动回填，数据源已被 P0.1 自己删除**——这是 PRD 两处决策打架，不是"误伤"。

> **2026-10-14 用户决定**：**手工填，不动 P0.1**。
>
> ✅ 已实现：家访表单 Step2 新增「被访人联系电话」输入框（`maxLength=20`），提交时写入 `contact_phone`，编辑模式回填。注释标注该字段不属 B.6 裁剪范围（家访业务必需）。
>
> ⚠️ **PRD §7.1「自动回填」措辞需修订为「手工填写」**，B.4 第 5 列保留不变。

### 2.4 `profile_edit` 审批通过后空转 ⚠️

`backend/app/portrait/services/submission_service.py:15-16`（文件头自述）

```
- profile_edit   : 暂不应用 field 改动 (P5+ 接入)
```

`approve()` 只有两个联动分支：`special_work`（`:361` 写 ledger）、`activity_claim`（`:378` 写 ActivityRecord）。**`profile_edit` 无任何分支** → 员工提交档案修改 → 管理员点通过 → 档案没变。

`profiles.py:133` 有注释「按用户 2026-10-10 决策改为 admin 直改」，但 **PRD 未同步这条决定**。

→ 属**决策项 5**。

### 2.5 `init_admin_user` 从未被调用，PRD 描述的默认管理员建不出来 ⚠️

PRD §16.1 描述首次使用创建 `ehr_id=0000001 / pwd=1234567` 的默认管理员。`app/db/init_db.py:88` 定义了该函数，**全项目零调用点**。`init_db()` 实际走 `crud.user.create(ehr_id="admin")`——**5 位非数字**，违反模型自身 `String(7)` 与 §3.2 的 7 位约束。

---

## 三、功能缺失（20+ 条）

### 家访（最大缺口）

| 编号 | 功能 | 状态 |
|---|---|---|
| F11 | 家访批量导入（B.4 的 14 列模板） | ❌ `templates.py` 只有 training/entry-exit/drill 三个模板 |
| F12 | 家访年度矩阵（员工 × 年份） | ❌ 后端无端点，前端无 Tab |
| — | 家访导出 `家访明细表_YYYY-MM-DD_HHmm.xlsx` | ❌ 无端点（§13 和 §16.3 均要求） |
| C3-2/3/4 | 预览打印 / 导出 PDF | ❌ 全无，全仓 grep `window.print` 无命中 |
| G8 | 我的家访（"我作为家访人的记录"） | ❌ 实际过滤的是"被访人属本组"，且无 `visitor_user_id` 过滤参数 |
| C2 | 列表筛选 5 项 | ⚠️ 后端只有 `status`/`visit_year`/`visited_ehr_id`；前端只传 `status` |
| C1-5 | 双人家访必填 2 人 | ⚠️ 前端标签直接写「第二家访人 (可选)」，后端 `Optional` |
| C1-7 | 扫描件必填 + `scan_status` 状态 | ⚠️ 标签写「(可选)」，且 **`scan_status` 字段模型里不存在** |

### 审批工作台

| 编号 | 功能 | 状态 |
|---|---|---|
| E1-1 | 聚合 4 类审批 | 🔀 家访是独立状态机 + 独立端点，`VALID_TYPES` 只有 3 类，**家访不出现在审批工作台** |
| E1-3 | 批量勾选 + 批量通过/驳回 | ❌ 无 `rowSelection`，后端无 bulk 端点 |
| E1-4/E3-4 | 筛选（类型/状态/时间/申请人） | ❌ 端点只收 `skip`/`limit` |
| E3-3 | 默认近 30 天 | ❌ 无时间参数，打开即全量 |
| E3-5 | Excel 导出 | ❌ 无 |
| E2-2 | 申请人档案摘要 | ❌ 无 |
| E2-6 | 转交选审批人 | ⚠️ 是 `<Input type="number">` **手输用户 ID**，且备注非必填；不校验对方是否为合法审批人 |
| E2-9 | 站内信通知 | ❌ 全模块不存在 |
| G3 | 组长替组员提交 | ❌ `SubmissionCreate` 无 `on_behalf_of_user_id` 字段 |

### 个人档案

| 编号 | 功能 | 状态 |
|---|---|---|
| D2 | 3 个折叠区（出入境/消防演练/培训） | ⚠️ 14 个 Tab 里**只有 `training`**，另两个不在个人档案页；后端无 `/me` 语义端点 |
| A4 | 兴趣 1:N 子表 | 🔀 只有 `PUT /me/interest` 单条 upsert，**只能存一条** |
| A5 | 获奖 1:N 子表 | 🔀 同上，**只能记一条获奖**，与"倒序排序"的存在意义冲突 |
| B3 | Tab + 筛选 | ❌ 单一 Table，无 Tab |
| A2 | 必填校验 | ⚠️ `ProfileUpdate` 7 字段全 `Optional`，前端也无 required 规则 |

### 其他

| 编号 | 功能 | 状态 |
|---|---|---|
| F15 | 顶部统计卡 | ❌ 后端只返回 `items/total` |
| F15 | 重置密码 | ❌ 无端点，但 `HelpPage.tsx:246` 已对外承诺该功能 |
| F16 | 批量换组 | ❌ 无端点无入口 |
| G1 | 组员花名册 | ❌ `TeamMembers.tsx` 挂在 admin 路由下，组长无入口；用户表无在岗状态字段 |
| G3 | 编辑组员信息 | ❌ `policy.csv` 无 `leader, user, edit` |
| G6 | 组长简易版演练登记 | ❌ `_require_admin` 硬拦，与 §13 明文相反 |
| F2 | 快速勾选表 | ❌ 是普通 `Select` 下拉，无团队筛选/全员清空/已选计数 |
| F4 | 城市/办公地点列 | ❌ `User` 模型无 `city`/`office_location` |
| F4 | 年度筛选 | ❌ `/drills/matrix` 无 `year` 参数 |
| A11 | 应急先锋队 | ⚠️ 后端支持 `target_user_id`，前端只传自己的 id，**管理员改不了他人** |
| G7 | 调组原因 | ⚠️ `record_transfer(reason=)` 三个调用点**全未传**，前端"调组原因"列恒显 `—` |

---

## 四、需业务确认（12 项 · 本报告核心）

> 每项均写成**可直接回答**的形式。

### 决策项 1 · 演练矩阵要不要包含零参加者？✅ 已拍板（2026-10-14）

**用户决定（第二轮修订）**：行集改为**基准全员**——但"全员"是相对**该查看者有权看的人**（admin=全行在职 / 组长=本组在职 / 普通员工=仅自己），停用账号排除。配套加**年份 + 团队筛选器**。

已实现，见 §1.2.1。⚠️ 遗留：`drill_service.matrix()` 对 admin 会一次载入全部在职员工（开发库 1494 人），列 × 行全展开，前端无虚拟滚动，大组下需观察性能。

### 决策项 1b · 家访矩阵的口径（本轮新增，已按现有代码定调）

F12 家访年度矩阵是本次新实现的，以下三条口径**PRD 未明写**，按代码现状记录，需要业务复核：

| 口径 | 本次实现 | 依据 |
|---|---|---|
| 行集 | 基准全员（同演练矩阵），权限按 §13 收口 | 与 F4 保持一致，否则"谁没被家访"看不见 |
| 单元格填什么 | 该年**具体家访日期**；同年多次显示 `2026-03-04 +2` | B.2 第 4-7 列要求填日期；次数是家访质量的一部分，只显示首次会误导 |
| 计入范围 | `approved` + `pending`；**draft / rejected / cancelled 一律不计** | 草稿还没提交、驳回撤回等于没访成。可用 `include_pending=false` 收紧为仅 approved |

> §7.2 写"仅绿色"、B.2 写"填具体日期"——两者不冲突：**日期是数据，绿色是它的呈现**，后端只给数据，前端着色。

### 决策项 2 · 管理员对家访到底是什么权限？🟠

代码给了**三种互相矛盾**的答案：

1. **创建时禁止**：`home_visit_service.py:106-107` 主动 403，注释写明业务理由"谁做家访谁签字"
2. **编辑时无拦截**：`routers/home_visits.py:206` 无 admin 判断（靠"建不了记录"被动挡住）
3. **扫描件上传主动放开**：`files.py:29-31` 注释明确写"MVP: admin + leader 都允许"

- **A. 只读**——补齐编辑的 admin 兜底 403，撤回 `files.py` 的放宽
- **B. 可代填**——放开编辑权限

### 决策项 3 · `visitor_info` 的"访人岗位"从哪来？✅ 已拍板（2026-10-14）

**用户决定**：按 PRD B.4 第 10 列原样。实现方式选**从用户表取**（`users.department`），且放在**后端**拼装。已实现，见 §2.2。

### 决策项 4 · 被家访人联系电话：自动回填还是手工填？✅ 已拍板（2026-10-14）

**用户决定**：**手工填，不动 P0.1**。已实现，见 §2.3。PRD §7.1 措辞需从"自动回填"改为"手工填写"。

### 决策项 5 · `profile_edit` 是废弃还是待补？🟠

2026-10-10 已决定改「admin 直改」但 PRD 未记。

- **A. 废弃**——下掉 `profile_edit` 提交类型，写进 §1.3 变更记录
- **B. 补联动**——`approve()` 里实现字段写回

### 决策项 6 · 用户禁用：砍硬删还是改软删？🟠

PRD §17.3 要求软删（`deleted_at`），实际 `db.delete()` 硬删；同时"禁用"（`is_active`）已实现且语义重叠。硬删 + SQLite `foreign_keys=0` → 误删即产生孤儿数据。

- **A. 只留禁用**——砍掉硬删按钮
- **B. 真软删**——引入 `deleted_at`，保留可恢复

### 决策项 7 · 「组长」以什么标识为准？🟠 长期根因

修这一条能同时解决 §13 里 8 个 ❌。

- **A. `Team.leader_id`**——已有真实组长标记，改 8 处 service 引用
- **B. 新增 `users.is_team_leader`**——显式字段
- **C. 启用 casbin `manager`**——与 `users.py` 的用户管理对齐

### 决策项 8 · PRD 自身矛盾：矩阵配色三处不一致 🟡

- §四 `:187` 写「黄绿蓝紫 4 色」
- §7.2 `:305` 和附录 B.5 `:873` 写「员工×年份 + **仅绿色**」
- 附录 B.2 `:804-808` 又要求单元格填**具体家访日期**而非颜色

### 决策项 9 · PRD 自身矛盾：导入模板列数 🟡

- 培训：§8.1 `:325` 写「6 列」，代码模板是 7 列（多 EHR 号）
- 出入境：§10.1.2 `:384` 写「17 个字段」，B.3 `:838` 写 EHR 移至序号后变 18 列，代码是 18 列

### 决策项 10 · 城市/办公地点字段从哪来？🟡

F4 宽矩阵要求这两列，全库无 `city`/`office_location`。

- **A. 用户表加列**
- **B. 演练表按行冗余**
- **C. 砍掉这两列**，PRD B.1 相应调整

### 决策项 11 · `portrait_operation_logs` 要接上吗？🟡

表已建（`action`/`resource`/`detail`/`ip` 字段齐备），但**零 insert 零 select**。PRD §16.5 声称"关键操作 100% 落库"，实际 0%。

- **A. 接上**——加中间件
- **B. 撤回 PRD 声明**——承认审计日志本期不做

### 决策项 12 · G3「组长可编辑本组员联系信息」是否已被隐私裁剪作废？🟡

PRD §11.2 写组长可编辑手机/邮箱/家庭地址，但附录 B.6 明确这些 ❌ 不存不展示。**两条直接冲突**，G3 可能整条已失效。

---

## 五、PRD 文档自身的问题（需修订，非代码问题）

| 问题 | 证据 |
|---|---|
| §13 权限矩阵把"操作日志"写了两遍 | 排版重复 |
| §17.1 声称 `FastAPI (async)` / `SQLAlchemy async` | 实际 `create_engine()` **同步** + `SessionLocal` 同步 `db.query()` |
| §17.3 声称用户软删 `deleted_at` | `app/models/user.py` **无此列**，`user_service.delete_user` 走 `db.delete()` 硬删 |
| §17.3 声称响应为 `UserResponse` 且不含 `password_hash` | 无 `UserResponse` 类；实际是 `schemas.User`，字段名 `hashed_password`——**PRD 早就写了这条，实现一直违反，2026-10-14 才修复** |
| §17.1 提及 `validators.py` | 该文件不存在，校验散落 6 个文件（`ehr_validator`） |
| §17.1 提及"操作日志自动埋点" | 无埋点调用 |
| §15 的 `/api/admin/*` 前缀 | **从未存在**；实际是 `/api/users` + `/api/portrait/*` 双前缀 |
| §14.2 "所有表加 `deleted_at`" | `models/_base.py:36` `PORTRAIT_TABLE_KWARGS = {}` 是**空 dict**，23 张表全无 |
| §14.2 EHR CHECK 约束 | ORM 层无 `CheckConstraint`，仅应用层 `ehr_validator.py` |
| §15 路径参数语义 | PRD 用 `/{ehr}`，代码用 `/{user_id}`；同域内 `profiles.py:72` 又确为 ehr，前后不统一 |
| §18 Q10 问偏了 | 问"PDF/Excel 之外的第三种导出格式"，而真正缺口（Excel 导出）未登记为开放问题 |
| §18 Q9 应随 A3 作废 | 标签数量限制已随 A3 下线，PRD 未标 |

### 代码有、PRD §14.1 ER 图未列的 5 张表

| 表 | 说明 |
|---|---|
| `portrait_development_intent` | 发展意向，1:1 挂 Profile |
| `portrait_project_summary` | 项目总结，**从未被写入**（§16.2 流程终点实际接到了台账 ledger） |
| `portrait_project_summary_tags` | 项目-技能标签 N:M，随 A3 下线成为孤儿 |
| `portrait_activity_record` | B2 审批通过后落地 |
| `portrait_user_metadata` | `is_first_login` + `deleted_at`，全项目唯一的软删表 |

---

## 六、系统性问题（非单个 bug）

### 6.1 权限体系分裂为三套

| 体系 | 覆盖域 | 判据 | 问题 |
|---|---|---|---|
| 手写 Python 分支（8 个 service） | profile / home_visit / entry_exit / training / group_transfer / submission | `is_superuser` + `team_id` | 8 处独立实现，同一套语义抄了 8 遍 |
| `is_superuser` 直判（4 个 router） | drill / entry_exit 写 / training 写 / files | 仅 `is_superuser` | 组长能力在这些域被整体抹掉 |
| casbin enforce（仅 `users.py`） | 用户管理 | casbin `manager`/`user` | `manager` 被当组长，且比 PRD 宽 |

`profile_service.py:26` 注释写着「Rule 7: 单一模式, Python 显式判断, 不混 Casbin」——但"单一模式"只统一了**写法**，没统一**判据**和**覆盖范围**。该注释在 `home_visit_service.py`、`training_service.py` 里被逐字复制了三遍。

### 6.2 同一张 `users` 表并存三套组别语义

`team_id`（portrait 隔离逻辑全用它）、`department`（`drill_service.py:92` 团队筛选、`:204` 矩阵"岗位"列都取它）、`team.name`。`group_transfer_service.py:10-12` 的注释已提过一次这个问题（"按名字过滤会让同名组互相看到"），但 drill 模块没跟进。

### 6.3 Excel 层与 API 层字段名分叉

出入境台账：Excel 模板列名已按 B.3 更新（`entry_exit.py:158-162`），ORM/API 仍是 `certificate_no`/`certificate_type`/`year`。导入能跑通，导出会串列。B.3 表格"数据库字段"列写的又是第三套名字（`passport_no`/`passport_type`/`depart_year`）。

### 6.4 死代码

`home_visit_service.py:66-79` `_can_view_record` 恒返回 `False`，**全项目零调用**；其注释提到的 `_ensure_can_view` 在 `home_visits.py` 里根本不存在。

### 6.5 认证错误码用在参数校验上

`training_service.py:28-29`、`entry_exit_service.py:21-23`：EHR 格式非法抛 **401**（语义是"没认证"，但调用方已认证），应为 400。

### 6.6 测试直接写开发库，测试隔离形同虚设 🔴 本次新发现

`backend/tests/conftest.py:12-19`

```python
@pytest.fixture(scope="session")
def db() -> Generator:
    db = SessionLocal()      # ← app.db.session.SessionLocal, 指向 taizhang.db
```

`SessionLocal` 绑定 `settings.SQLALCHEMY_DATABASE_URI`（= `sqlite:///.../taizhang.db`），**不是测试库**。而 `db_tests` / `services_tests` 另有自己的 conftest，portrait 测试用的是这个根 conftest。

**后果**：
- 每次 `pytest tests/portrait/` 都会**往开发库写入**演练、家访、用户等记录
- 测试失败时清理代码不执行 → 残留累积（本次审计在开发库发现 7 条测试残留演练记录，已经用户授权清理）
- **`backend/test_services.db` 虽被 git 跟踪，但 portrait 测试根本不写它**——跟踪它没有意义
- 若某天执行了破坏性迁移或清库操作，**会连带清掉开发数据**

> **本次影响**：`test_drill.py` 新增用例曾因断言写在 `try` 外而留下残留（已改为 `try` 内创建 + `finally` 清理）。
>
> **建议**（未实施，需单独排期）：给 `SessionLocal` 做依赖注入，让 `conftest` 指向独立测试库；同时 `backend/test_services.db` 应从 git 跟踪中移除。
>
> ⚠️ 修复前**跑测试前建议先备份 `taizhang.db`**。

#### 6.6.1 隔离测试库的踩坑记录（本次实测，已给出可行解法）🔴

`tests/portrait/test_home_visit_f11_f12.py` 是第一份**不写开发库**的 portrait 测试。它实测出一个反直觉的坑，值得记下来：

```python
app.dependency_overrides[deps.get_db] = my_isolated_get_db   # ❌ 不够
```

**只改路由参数 `db`，改不到 `get_current_user` 子依赖里那次调用**。表现是：请求里的 `current_user` 来自**开发库**，而 router 的 `db` 来自**内存库**——同一次请求里两个身份对不上，10 条用例全红，且报错信息（"仅组长可导入"）完全看不出是隔离问题，极易误判成业务 bug。排查花了很久才定位。

原因：`deps.py:11` 和 `deps.py:12` 分别 `from app.db.session import get_db / SessionLocal`，**同一个名字在两个模块里各存一份**；覆盖 override 没能穿透到子依赖的真实调用。

**可行的隔离写法**（本文件已采用，两个模块都要换）：

```python
from app.db import session as session_mod
from app.api import deps

factory = lambda: Session(bind=_TEST_ENGINE)
session_mod.SessionLocal = factory   # 真实 get_db 函数体里的那个名字
deps.SessionLocal = factory          # deps.py:12 又 import 了一份
```

配套要点：内存库必须 `poolclass=StaticPool`（否则每次新连接拿到一个全新空库）；固件 `admin_user` 这类必须 **session 级**且用固定 `ehr_id`（`ehr_id` 唯一，function 级会撞 UNIQUE）；本项目的"普通员工"只能用 `team_id=None` 的 user 代表，因为 `team_id` 非空即组长（§1.1）。

> ⚠️ 同样的隔离可以套到其余 6 个 portrait 测试文件上——那一步还没做，**在做完之前，跑 `pytest tests/portrait/` 仍会写开发库**。

---

## 七、已核实的正确实现（避免重复审计）

| 项 | 位置 |
|---|---|
| Token 60 分钟过期 | `config.py` `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60` |
| 品牌配色 `#D05A6E` | `App.css:9` + `App.tsx:55-67` AntD token |
| G7 换组历史**有**写入 | `user_service.py:137`、`team_service.py:230,263` 三个生产调用点 |
| 家访新建三道校验与 PRD 完全吻合 | `home_visit_service.py:106-123`（admin 禁 / 无组别禁 / 跨组禁） |
| 出入境写权限仅 admin | `entry_exit.py:53-56` `_require_admin` 守卫 4 个写端点 |
| 审计日志模型存在 | `models/log.py` `SystemLog` / `AuditLog`（但 portrait 侧未接，见决策项 11） |
| 批量导入的 Rule 12 反馈 | `BulkImportPage.tsx` 失败明细已用 `console.table` 显性化 |

---

## 附录 · Agent 误报纠正记录

审计采用 agent 并行核对 + 人工复核，以下结论**经反查后推翻**：

| Agent 结论 | 实际情况 |
|---|---|
| "`portrait_group_transfer_history` 零写入" | **错误**。有 3 个生产调用点：`user_service.py:137`、`team_service.py:230`、`team_service.py:263`。`test_group_transfer.py` 有 20+ 用例覆盖 |

记录此项是为了说明：并行审计的结论**均经过反查**，报告中的每条都经过独立验证，未直接采信 agent 输出。

---

> 报告版本：2026-10-14 · 对应代码分支 `feat/security-pbkdf2-60min-idle-first-login`
> 本次同步修复：§1.2 演练 viewer 过滤、§1.3 家访 None 越权、§2.1 审批人下拉回归
> 修复未提交，保留在工作区供审阅