# 后端测试

本目录包含后端的测试代码，用于验证API和数据库操作的功能和可用性。

## 测试目录结构

- `api/`: 包含各个API模块的测试文件
- `db_tests/`: 包含各个数据模型的数据库访问测试
- `conftest.py`: 全局pytest配置文件
- `run_api_tests.py`: 运行API测试的脚本
- `prepare_and_test.py`: 准备测试数据并运行API测试的脚本

## API测试

API测试位于`api/`目录下，用于验证各个API端点的功能：

- `test_workflows.py`: 工作流API测试
- `test_approvals.py`: 审批API测试
- `test_auth.py`: 认证API测试
- `test_templates.py`: 模板API测试
- `test_ledgers.py`: 台账API测试
- `test_logs.py`: 日志API测试
- `test_users.py`: 用户API测试
- `test_fields.py`: 字段API测试
- `test_roles.py`: 角色API测试
- `test_teams.py`: 团队API测试

### 运行API测试

```bash
# 准备测试数据并运行所有测试
python tests/prepare_and_test.py

# 运行特定的API测试
python tests/run_api_tests.py --run test_workflows

# 列出所有可用的测试
python tests/run_api_tests.py --list

# 运行所有API测试
python tests/run_api_tests.py --run all
```

## 数据库访问测试

数据库测试位于`db_tests`目录下，用于测试各模型的CRUD操作。每个测试模块对应一个数据模型：

- `test_user_db.py`: 用户模型测试
- `test_role_db.py`: 角色模型测试
- `test_team_db.py`: 团队模型测试
- `test_template_db.py`: 模板模型测试
- `test_field_db.py`: 字段模型测试
- `test_ledger_db.py`: 台账模型测试
- `test_ledger_item_db.py`: 台账条目模型测试
- `test_workflow_db.py`: 工作流模型测试
- `test_permission_db.py`: 权限管理测试

### 运行数据库测试

```bash
# 运行所有数据库测试
pytest tests/db_tests/

# 运行特定模型的测试
pytest tests/db_tests/test_user_db.py

# 运行特定测试函数
pytest tests/db_tests/test_user_db.py::test_create_user
```

详细信息请参见 [数据库测试README](./db_tests/README.md)。

## 最近修改

### 数据库访问测试添加

我们添加了一系列数据库访问测试，专注于验证各模型的CRUD操作和相关业务逻辑的正确性：

1. 添加了`db_tests`目录，包含各模型的测试文件
2. 添加了测试fixture，用于创建临时测试数据
3. 实现了用户、角色、团队、模板、字段、台账等模型的测试

### email字段移除

我们已完成从User模型中移除email字段并替换为ehr_id的工作：

1. 修改了`app/api/api_v1/endpoints/users.py`中的用户创建和导入代码
2. 修改了`app/crud/crud_user.py`中的用户查询方法
3. 修改了`create_test_users.py`中的测试用户创建代码
4. 修改了前端代码中的用户导入模板和提示文本

### 审批API测试修复

修改了审批API测试，使其与实际API路由匹配：

1. 将期望的`/approvals/`路由改为`/approvals/tasks`、`/approvals/ledgers`等实际路径
2. 添加了更全面的测试，包括提交审批、审批通过和拒绝等功能

## 测试方法

测试采用以下方法：

1. **API测试**：使用FastAPI的TestClient进行API测试，模拟不同用户角色
2. **数据库测试**：使用pytest直接测试CRUD操作，验证模型和数据库交互的正确性

## 注意事项

1. 测试会创建测试数据，包括用户、模板、工作流和台账等
2. 测试会使用数据库，确保使用测试数据库而不是生产数据库
3. 某些测试用例可能会根据数据库中的现有数据有不同的行为 