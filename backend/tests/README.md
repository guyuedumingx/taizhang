# 后端API测试

本目录包含后端API的测试代码，用于验证API的功能和可用性。

## 测试文件结构

- `api/`: 包含各个API模块的测试文件
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
- `run_api_tests.py`: 运行API测试的脚本
- `prepare_and_test.py`: 准备测试数据并运行API测试的脚本
- `conftest.py`: pytest配置文件

## 测试方法

测试采用以下方法：

1. 使用FastAPI的TestClient进行API测试
2. 模拟不同用户角色（管理员、普通用户）
3. 测试API的各种功能和边界情况
4. 验证API的响应状态码和响应内容

## 最近修改

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

## 运行测试

### 准备测试数据并运行所有测试

```bash
python tests/prepare_and_test.py
```

这个脚本会先准备测试数据，然后运行所有API测试。

### 运行特定的API测试

```bash
python tests/run_api_tests.py --run test_workflows
```

### 列出所有可用的测试

```bash
python tests/run_api_tests.py --list
```

### 运行所有API测试

```bash
python tests/run_api_tests.py --run all
```

## 测试结果

所有API测试现在都已通过，证明API功能正常工作。

## 注意事项

1. 测试会创建测试数据，包括用户、模板、工作流和台账等
2. 测试会使用数据库，确保使用测试数据库而不是生产数据库
3. 某些测试用例可能会根据数据库中的现有数据有不同的行为 