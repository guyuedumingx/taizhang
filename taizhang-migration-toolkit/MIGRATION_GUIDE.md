# 台账管理系统迁移工具包

## 概述

本工具包包含了台账管理系统数据库迁移的相关脚本和文档，支持以下迁移路径：

- **Oracle → SQLite**：将内网 Oracle 数据库迁移到本地 SQLite
- **Oracle → Oracle**：在两个 Oracle 实例之间迁移数据（如从内网迁移到外网）

## 文件说明

### 1. 核心迁移脚本

- `migrate_oracle_to_sqlite.py` - Oracle → SQLite 数据迁移
- `migrate_oracle_to_oracle.py` - Oracle → Oracle 数据迁移
- `migrate_auto_fill_config.py` - 自动填充配置升级脚本，为 templates 表添加 auto_fill_config 字段

### 2. 文档

- `README.md` - 开发环境搭建说明（包含了完整的环境配置指南）
- `requirements.txt` - Python 依赖包列表（需要额外安装 cx_Oracle）

## 使用步骤

### 1. Oracle → SQLite 迁移（如需要）

#### 前置条件
- Python 3.9 环境
- 安装 cx_Oracle: `pip install cx_Oracle`
- Oracle Instant Client 19c（需要添加到 PATH）

#### 配置迁移脚本
编辑 `migrate_oracle_to_sqlite.py` 中的配置：

```python
# 第38-45行 - 配置区
ORACLE_CONFIG = {
    "user": os.getenv("ORACLE_USER", "your_username"),
    "password": os.getenv("ORACLE_PASSWORD", "your_password"),
    "dsn": os.getenv("ORACLE_DSN", "host:port/service_name"),
}

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "taizhang.db")
```

#### 执行迁移
```bash
# 在 backend 目录下运行
python migrate_oracle_to_sqlite.py
```

迁移完成后，将生成的 `taizhang.db` 文件复制到项目的 `backend/` 目录下，然后修改后端配置使用 SQLite。

### 2. 数据库 Schema 升级（如果需要自动填充功能）

```bash
# 在 backend 目录下运行
python -m app.db.migrate_auto_fill_config
```

这个脚本会为 templates 表添加 `auto_fill_config` 列。

### 3. Oracle → Oracle 迁移

#### 适用场景
- 内网 Oracle 迁移到外网 Oracle
- 开发环境同步生产环境数据
- Oracle 服务器升级/更换

#### 前置条件
- Python 3.9 环境
- 安装 cx_Oracle: `pip install cx_Oracle`
- Oracle Instant Client 19c（需要添加到 PATH）
- **目标 Oracle 库已通过 Alembic 或 init_db 创建好表结构**

#### 配置迁移脚本

编辑 `.env` 文件（参考 `.env.example`），设置源库和目标库的连接信息：

```env
# 源 Oracle 配置
SOURCE_ORACLE_USER=source_username
SOURCE_ORACLE_PASSWORD=source_password
SOURCE_ORACLE_DSN=192.168.1.100:1521/source_orcl

# 目标 Oracle 配置
TARGET_ORACLE_USER=target_username
TARGET_ORACLE_PASSWORD=target_password
TARGET_ORACLE_DSN=192.168.2.100:1521/target_orcl
```

#### 执行迁移
```bash
# 在 taizhang-migration-toolkit 目录下运行
python migrate_oracle_to_oracle.py
```

#### 迁移选项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BATCH_SIZE` | 500 | 每批插入的行数 |
| `TRUNCATE_BEFORE_INSERT` | true | 是否在插入前清空目标表 |

#### 注意事项
- Oracle → Oracle 迁移会**保留原始 ID**，并自动更新目标库的自增序列
- 两端 Oracle 版本建议相同或相近（同为 19c 等）
- 目标库需要提前创建好表结构（通过 Alembic 或 init_db）
- 迁移前建议备份目标库

## 环境配置参考

详细的开发环境配置指南请参考 `README.md`（原环境.md文档），包含：
- 前后端环境搭建
- 依赖安装
- 数据库配置
- 启动方式
- 常见问题排查

## 注意事项

1. **备份**：执行迁移前请务必备份原有数据
2. **测试**：建议先在测试环境执行完整流程
3. **权限**：确保数据库用户有足够的读写权限
4. **依赖**：迁移脚本依赖 cx_Oracle，需要确保 Oracle 客户端正确安装

## 迁移后的调整

1. 修改后端配置（backend/.env）：
   - 将 `DATABASE_TYPE` 从 `oracle` 改为 `sqlite`
   - 移除 Oracle 相关配置
   - 确保指向正确的 SQLite 数据库文件路径

2. 如果使用 Oracle 迁移到 SQLite，后端代码可能需要以下调整：
   - 移除 cx_Oracle 相关的 import
   - 确保所有 SQL 查询兼容 SQLite

## 常见问题

1. **cx_Oracle 安装失败**
   - 确保使用 64 位 Python 和 64 位 Oracle Instant Client
   - 下载对应版本的 Instant Client 并添加到 PATH

2. **迁移中途失败**
   - 检查 Oracle 连接配置
   - 确保有足够的磁盘空间
   - 查看控制台错误信息

3. **SQLite 运行时报错**
   - 确保 SQLite 文件路径正确
   - 检查文件权限
   - 确认数据库文件存在

## 支持

如有问题，请参考原项目文档或联系开发团队。