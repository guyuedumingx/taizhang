# API 端点清单

> **路由前缀**：`/api/v1/`（在 `core/config.py` 定义为 `API_V1_STR`）
> **鉴权方式**：JWT Bearer Token（OAuth2PasswordBearer）
> **Token 来源**：`POST /api/v1/auth/login` → `{access_token, token_type: "bearer", ...}`

---

## 路由总览（13 个模块）

| 模块 | 路径前缀 | 来源 | 完整度 |
|---|---|---|---|
| 认证 | `/auth` | `endpoints/auth.py` | ✅ 读过 |
| 用户管理 | `/users` | `endpoints/users.py` | ✅ 读过 80 行 |
| 团队管理 | `/teams` | `endpoints/teams.py` | ⚠️ 未读 |
| 角色管理 | `/roles` | `endpoints/roles.py` | ⚠️ 未读 |
| 台账管理 | `/ledgers` | `endpoints/ledgers.py` | ⚠️ 未读 |
| 模板管理 | `/templates` | `endpoints/templates.py` | ⚠️ 未读 |
| 工作流管理 | `/workflows` | `endpoints/workflows.py` | ⚠️ 未读 |
| 工作流节点 | `/workflow-nodes` | `endpoints/workflow_nodes.py` | ⚠️ 未读 |
| 工作流实例 | `/workflow-instances` | `endpoints/workflow_instances.py` | ⚠️ 未读 |
| 审批管理 | `/approvals` | `endpoints/approvals.py` | ⚠️ 未读 |
| 日志管理 | `/logs` | `endpoints/logs.py` | ⚠️ 未读 |
| 统计分析 | `/statistics` | `endpoints/statistics.py` | ⚠️ 未读 |
| 自动填充配置 | `/auto-fill-configs` | `endpoints/auto_fill_configs.py` | ⚠️ 未读 |
| 测试 | `/test-token` | `api.py` 调试用 | ✅ 已读 |

---

## 已确认的端点模式（基于 users.py 读到的 80 行）

所有 endpoint 的标准模式：

```python
@router.get("/", response_model=schemas.PaginatedResponse[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),                    # 1. DB session
    skip: int = 0,
    limit: int = 1000,
    current_user: models.User = Depends(deps.get_current_active_user),  # 2. 当前用户
) -> Any:
    # 3. 业务逻辑
    ...
```

**关键依赖**（来自 `core/deps.py`）：
- `deps.get_db` - DB session（generator）
- `deps.get_current_user` - 解析 JWT，返回 User
- `deps.get_current_active_user` - 要求 is_active=True
- `deps.get_current_active_superuser` - 要求 is_superuser=True
- `deps.check_permissions(resource, action, current_user)` - Casbin 权限检查

---

## 已确认的端点（从 users.py 读到的）

| Method | Path | 用途 | 权限 |
|---|---|---|---|
| GET | `/users/` | 用户列表（分页） | 任意登录用户 |
| POST | `/users/` | 创建用户 | `user:create` |
| GET | `/users/{user_id}` | 用户详情 | `user:view` 或本人 |
| GET/PATCH/DELETE | `/users/{user_id}/...` | 其他用户操作（具体路径未读完） | |

> ⚠️ 完整端点路径、参数、返回值**未完整记录**，需补充读 `endpoints/users.py` 全文。

---

## 已确认的认证流程（从 auth_service.py 读到的）

```
POST /api/v1/auth/login
Body: {ehr_id: "0000001", password: "..."}

Service: AuthService.authenticate_user(db, ehr_id, password)
  1. db.query(User).filter(ehr_id).first()
  2. verify_password(plain, hashed_password)  [bcrypt]
  3. check is_active
  4. get_roles_for_user(user.id)  [Casbin]
  5. get_permissions_for_role(role)
  6. check password_expired = (last_password_change < now - 90天)
  7. create_access_token({sub: str(user.id), roles})
  8. return {access_token, token_type, user_id, username, name,
            roles, password_expired, permissions, team_id}
```

**响应示例**（推断）：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin",
  "name": "管理员",
  "roles": ["admin", "user"],
  "password_expired": false,
  "permissions": ["user:view", "user:create", "ledger:*", ...],
  "team_id": 1
}
```

---

## 已确认的关键路由（推断 + 已知功能）

基于已读的代码和服务，台账的核心路由应该包括（**未完整验证**）：

| 推断路径 | 推断用途 | 依据 |
|---|---|---|
| `POST /auth/login` | 登录 | auth_service.authenticate_user |
| `GET /auth/me` | 当前用户信息 | 标准 FastAPI 模式 |
| `POST /auth/register` | 注册 | auth_service.register_user |
| `POST /auth/change-password` | 改密 | auth_service.change_password |
| `GET/POST /users/` | 列表/创建 | endpoints/users.py 确认 |
| `GET/POST /teams/` | 团队 | endpoints/teams.py |
| `GET/POST /roles/` | 角色 | endpoints/roles.py |
| `GET/POST /ledgers/` | 台账列表/创建 | ledger_service.get_ledgers |
| `POST /ledgers/{id}/submit` | 提交台账 | 创建 workflow_instance |
| `GET/POST /templates/` | 模板管理 | template_service |
| `GET/POST /workflows/` | 工作流管理 | workflow_service |
| `GET/POST /approvals/` | 审批操作 | workflow_instance.approve/reject |
| `GET /approvals/pending` | 待办列表 | CRUDWorkflowInstanceNode.get_user_pending_tasks |
| `POST /approvals/{node_id}/approve` | 审批通过 | CRUDWorkflowInstance.approve_current_node |
| `POST /approvals/{node_id}/reject` | 审批驳回 | CRUDWorkflowInstance.reject_current_node |
| `GET /logs/` | 日志查询 | endpoints/logs.py |
| `GET /statistics/...` | 统计 | endpoints/statistics.py |
| `GET/POST/PUT/DELETE /auto-fill-configs/` | 自动填充配置 | endpoints/auto_fill_configs.py |

---

## 前端 API 客户端（基于目录结构）

`frontend/src/api/` 下 13 个文件，每个对应一个后端模块：

| 前端 API 文件 | 对应后端路径 |
|---|---|
| `approvals.ts` | `/approvals/*` |
| `autoFill.ts` | （前端工具） |
| `autoFillConfigs.ts` | `/auto-fill-configs/*` |
| `index.ts` | 统一导出 |
| `ledgers.ts` | `/ledgers/*` |
| `logs.ts` | `/logs/*` |
| `roles.ts` | `/roles/*` |
| `teams.ts` | `/teams/*` |
| `templates.ts` | `/templates/*` |
| `users.ts` | `/users/*` |
| `util.ts` | 工具（request 拦截器） |
| `workflow_instances.ts` | `/workflow-instances/*` |
| `workflow_nodes.ts` | `/workflow-nodes/*` |
| `workflows.ts` | `/workflows/*` |

**前端 services 层**（业务封装）：`LedgerService.ts / LogService.ts / RoleService.ts / TeamService.ts / TemplateService.ts / UserService.ts / WorkflowService.ts`

---

## ⚠️ 必须后续补完的内容

1. **每个 endpoint 文件的完整端点列表**：12 个未读文件，每个约 100-300 行
2. **每个 endpoint 的 Request/Response Schema**：`schemas/*` 13 个文件未读完整
3. **错误码**：哪些 4xx/5xx 在什么时候返回
4. **特殊接口**：导入 Excel 的 endpoint、导出 Word/Excel 的 endpoint
5. **分页参数**：skip/limit 还是 page/size？

---

## AI 制定方案时如何使用本文档

- 当用户问"前端怎么调用用户列表" → 看 `users.ts`，但需要后端 `/users/` 的入参格式（**未记录完整**）
- 当用户问"审批怎么调" → 看 `approvals.ts` + 后端 `/approvals/`（**需要补充读 endpoints**）
- 当用户问"前端 token 怎么存" → 看 `stores/authStore.ts`（**未读**）

**建议**：在制定任何对接方案前，先 `Read` 完整的 `endpoints/auth.py` 和 `endpoints/ledgers.py`（最高优先级）。