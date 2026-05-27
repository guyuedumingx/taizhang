# 开发环境搭建

本文档说明如何在 Windows 10 个人 PC 上搭建台账管理系统（`taizhang`）的本地开发环境。所有命令均假设在仓库根目录 `/Users/zhuojialin/taizhang` 下执行。

## 1. 前置条件

| 软件 | 推荐版本 | 说明 |
| --- | --- | --- |
| Windows | Windows 10 | 需具备管理员权限 |
| Python | 3.9.x | 建议从 python.org 获取官方安装包，安装时勾选 “Add Python to PATH” |
| Node.js | 18 LTS | 自动包含 npm |
| Git | 2.30+ | 用于拉取代码 |
| Oracle Instant Client | 19c Basic | 供 `cx_Oracle` 使用，安装后将 `instantclient` 目录加入 `PATH` |
| Nginx | 最新稳定版 | Windows 版，用于前端静态托管 |

> **提示**：首次运行前，请确认本机能够通过局域网访问 Oracle 19c 服务器，并取得数据库账号、service name 等连接信息。

## 2. 拉取代码

```bash
git clone <仓库地址> taizhang
cd taizhang
```

## 3. 后端环境

### 3.1 创建并激活虚拟环境

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

### 3.2 安装依赖

```powershell
pip install -r requirements.txt
```

如果提示缺少 VC++ 运行库，请安装 [Microsoft Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)。

### 3.3 配置 `.env`

在 `backend` 目录下创建 `.env` 文件（使用 PowerShell：`New-Item -Path .env -ItemType File`），推荐模板如下：

```env
PROJECT_NAME=台账管理系统
API_V1_STR=/api/v1

# JWT
SECRET_KEY=<随机生成的32位密钥>
ACCESS_TOKEN_EXPIRE_MINUTES=4320  # 8 天

# 数据库（Oracle 远程实例）
DATABASE_TYPE=oracle
ORACLE_USER=<用户名>
ORACLE_PASSWORD=<密码>
ORACLE_HOST=<Oracle服务器IP>
ORACLE_PORT=1521
ORACLE_SERVICE=<service_name>

# 连接池可选配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# CORS
CORS_ORIGINS=["http://localhost:5173"]

# 首次部署用完后可清空
FIRST_SUPERUSER=admin
FIRST_SUPERUSER_PASSWORD=<初始密码>
```

> `.env` 内含敏感信息，请通过 `icacls` 或 BitLocker/EFS 等方式限制访问。

### 3.4 数据库初始化

系统默认访问 Oracle 19c 远程库，无需本机安装数据库。首次搭建时仍需创建表结构：

```powershell
alembic upgrade head
python -m app.db.init_db
```

如需导入测试用户，可执行 `python create_test_user.py`。

### 3.5 启动后端

开发模式：

```powershell
python main.py
```

默认监听 `0.0.0.0:8080`。可访问 `http://localhost:8080/api/v1/docs` 查看 Swagger。

## 4. 前端环境

### 4.1 安装依赖

```powershell
cd ..\frontend
npm install
```

### 4.2 配置接口地址（可选）

开发阶段前端默认请求 `/api/v1`，当后端运行在本机的 `8080` 端口时无需额外配置。如需显式指定，可在 `frontend` 目录下创建 `.env.local`：

```env
VITE_API_URL=http://localhost:8080/api/v1
```

### 4.3 启动开发服务器

```powershell
npm run dev
```

访问 `http://localhost:5173` 即可调试前端。

### 4.4 构建生产包

```powershell
npm run build
```

构建结果位于 `frontend/dist`，复制至 Nginx `html` 目录即可用于部署。

## 5. Nginx 简易配置（本地调试/部署）

在 `nginx/conf/nginx.conf` 的 `http` 区域新增 server 配置：

```nginx
server {
    listen       80;
    server_name  localhost;

    root   C:/nginx/html;
    index  index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

重新加载配置：`nginx -s reload`。

## 6. 环境验证清单

- `http://localhost:8080/` 返回 `{"message":"台账管理系统API服务"}`
- `http://localhost:8080/api/v1/docs` 可正常打开
- 前端 `npm run dev` 后访问 `http://localhost:5173`，完成一次登录 → 台账查询 → 导出流程
- Oracle 远程库可执行 `SELECT 1 FROM dual;`

## 7. 常见问题

| 问题 | 排查步骤 | 解决方案 |
| --- | --- | --- |
| `cx_Oracle.DatabaseError: DPI-1047` | 检查 Instant Client 是否安装并在 `PATH` 中 | 下载 64 位 Instant Client 19c，解压后将路径加入系统环境变量，重启终端 |
| 无法连接 Oracle | 使用 `tnsping <service>` 测试网络，确认 `.env` 配置 | 修正主机/端口/service name，核对账号密码；检查局域网 ACL |
| Python 依赖编译失败 | 查看报错中缺少的编译环境 | 安装 Visual C++ Build Tools 或运行 `pip install --upgrade pip setuptools wheel` |
| 前端请求 404 / CORS | 检查前端 API 基础路径和后端 CORS 配置 | 在 `.env` 中调整 `CORS_ORIGINS`，确保 Nginx 代理到正确地址 |
| 端口冲突 | PowerShell 执行 `netstat -ano | findstr :8080` | 停止占用进程或修改后端启动端口 |

### Oracle 性能调优建议

- **索引规划**：确保在高频查询条件上存在索引，例如 `ledgers.team_id`、`ledgers.template_id`、`workflow_instances.ledger_id`、`workflow_instance_nodes.workflow_instance_id/current_node_id` 等列。
- **统计信息**：定期执行 `EXEC DBMS_STATS.GATHER_TABLE_STATS('<schema>', '<table>');` 和 `EXEC DBMS_STATS.GATHER_INDEX_STATS('<schema>', '<index>');`，确保优化器掌握最新统计数据。
- **游标批量参数**：通过环境变量 `ORACLE_CURSOR_ARRAYSIZE`、`ORACLE_CURSOR_PREFETCHROWS` 调整游标 `arraysize` / `prefetchrows`，配合 SQLAlchemy 事件自动设置，减少往返次数。
- **性能监控**：调用 `/api/v1/statistics/pool-status` 查看连接池使用率，结合 AWR/ASH 或 `V$` 视图观察 SQL 等待事件，及时扩容或优化。
- **分页与批量**：台账列表建议分页或滚动加载，避免一次性拉取数百条记录；对于导出类场景优先使用后台任务或流式处理。

## 8. 参考

- Oracle Instant Client 下载：<https://www.oracle.com/database/technologies/instant-client/downloads.html>
- FastAPI 文档：<https://fastapi.tiangolo.com/>
- Ant Design 组件库：<https://ant.design/>
- Alembic 文档：<https://alembic.sqlalchemy.org/>