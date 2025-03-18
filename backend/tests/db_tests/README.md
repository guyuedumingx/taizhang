# 台账系统数据库访问测试

本目录包含台账系统的数据库访问测试，专注于验证各模型的CRUD操作和相关业务逻辑的正确性。

## 测试模块

每个测试模块对应一个数据模型：

- `test_user_db.py` - 用户模型测试
- `test_role_db.py` - 角色模型测试
- `test_team_db.py` - 团队模型测试
- `test_template_db.py` - 模板模型测试
- `test_field_db.py` - 字段模型测试
- `test_ledger_db.py` - 台账模型测试
- `test_ledger_item_db.py` - 台账条目模型测试
- `test_workflow_db.py` - 工作流模型测试
- `test_permission_db.py` - 权限管理测试

## 测试数据

测试数据在`conftest.py`文件中定义，包括以下主要fixture：

- `db` - 数据库会话
- `test_user` - 测试用户数据
- `test_admin` - 测试管理员数据
- `test_team` - 测试团队数据
- `test_role` - 测试角色数据
- `test_template` - 测试模板数据
- `test_field` - 测试字段数据
- `test_workflow` - 测试工作流数据
- `test_ledger` - 测试台账数据

## 运行测试

每个测试函数都是独立的，可以单独运行。测试会自动创建一个临时数据库，并在测试完成后清理。

```bash
# 进入backend目录
cd backend

# 运行所有数据库测试
pytest tests/db_tests/

# 运行特定模型的测试
pytest tests/db_tests/test_user_db.py

# 运行特定测试函数
pytest tests/db_tests/test_user_db.py::test_create_user
```

## 测试功能

每个测试模块通常包含以下测试：

1. **创建记录**：测试创建新记录的功能，验证数据是否正确存储
2. **读取记录**：测试根据ID获取记录的功能
3. **更新记录**：测试更新现有记录的功能
4. **删除记录**：测试删除记录的功能
5. **批量获取**：测试获取多条记录的功能
6. **特定业务逻辑**：如权限检查、关联关系等

## 权限测试

`test_permission_db.py`专门测试基于Casbin的权限管理系统，包括：

- 角色权限的添加和删除
- 用户角色的添加和获取
- 权限检查逻辑
- 超级用户权限

## 编写新测试

1. 导入必要的模块：
   ```python
   import pytest
   from sqlalchemy.orm import Session
   from app import crud, models, schemas
   ```

2. 使用注入的fixtures：
   ```python
   def test_something(db: Session, test_user: dict):
       # ...测试代码
   ```

3. 创建测试对象：
   ```python
   obj_in = schemas.SomeModelCreate(**test_data)
   obj = crud.some_model.create(db, obj_in=obj_in)
   ```

4. 使用断言验证结果：
   ```python
   assert obj.name == expected_name
   assert obj.id is not None
   ``` 