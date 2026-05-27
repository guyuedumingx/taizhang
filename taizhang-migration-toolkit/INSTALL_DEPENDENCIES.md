# 依赖安装指南

## 自动安装（推荐）

在迁移工具包目录下运行：

```bash
pip install python_dotenv-1.2.1-py3-none-any.whl
```

## 手动安装

如果上述方法失败，可以使用 pip 安装：

```bash
pip install python-dotenv
```

或者直接安装 requirements.txt 中的所有依赖：

```bash
pip install -r requirements.txt
```

## 注意事项

- 工具包中已包含 `python_dotenv-1.2.1-py3-none-any.whl`，可以直接安装
- 如果内网环境无法访问 PyPI，需要手动下载其他依赖包
- 运行环境检查脚本会自动检测是否安装成功

## 验证安装

运行环境检查脚本：

```bash
python check_migration_env.py
```

如果 python-dotenv 已安装，会显示：`✓ python-dotenv`