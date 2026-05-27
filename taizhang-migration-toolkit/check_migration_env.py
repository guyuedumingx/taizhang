#!/usr/bin/env python3
"""
迁移环境检查脚本
检查运行迁移所需的环境和依赖
"""

import sys
import os
import importlib.util

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✓ Python 版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python 版本过低: {version.major}.{version.minor}.{version.micro} (需要 3.9+)")
        return False

def check_required_packages():
    """检查必需的 Python 包"""
    required_packages = {
        'fastapi': 'FastAPI',
        'sqlalchemy': 'SQLAlchemy',
        'pydantic': 'Pydantic',
        'python_dotenv': 'python-dotenv'
    }

    optional_packages = {
        'cx_Oracle': 'cx_Oracle (Oracle 迁移需要)',
    }

    print("\n检查必需包:")
    all_required_ok = True
    for package, name in required_packages.items():
        spec = importlib.util.find_spec(package)
        if spec is not None:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - 未安装")
            all_required_ok = False

    print("\n可选包:")
    all_optional_ok = True
    for package, name in optional_packages.items():
        spec = importlib.util.find_spec(package)
        if spec is not None:
            print(f"✓ {name}")
        else:
            print(f"⚠ {name} - 未安装 (如果需要 Oracle 迁移，请安装)")
            all_optional_ok = False

    return all_required_ok, all_optional_ok

def check_oracle_instant_client():
    """检查 Oracle Instant Client"""
    try:
        import cx_Oracle
        # 尝试获取版本信息
        version = cx_Oracle.clientversion()
        print(f"\n✓ Oracle Instant Client 已安装 (版本: {version})")
        return True
    except ImportError:
        print("\n⚠ Oracle Instant Client 未安装 (cx_Oracle 无法导入)")
        print("  下载地址: https://www.oracle.com/database/technologies/instant-client/downloads.html")
        return False
    except Exception as e:
        print(f"\n⚠ Oracle Instant Client 可能有问题: {e}")
        return False

def check_sqlite_file():
    """检查 SQLite 文件（如果存在）"""
    sqlite_files = ['taizhang.db', 'backend/taizhang.db']
    found = False
    for db_file in sqlite_files:
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"\n✓ 找到 SQLite 数据库: {db_file} (大小: {size} 字节)")
            found = True

    if not found:
        print("\nℹ 未找到 SQLite 数据库文件")
        print("  如果需要从 Oracle 迁移，将自动创建")

def show_migration_checklist():
    """显示迁移检查清单"""
    print("\n" + "="*60)
    print("迁移前检查清单")
    print("="*60)

    print("\n1. 数据备份:")
    print("   [ ] 已备份 Oracle 数据库")
    print("   [ ] 已保存所有配置文件")

    print("\n2. 环境准备:")
    print("   [ ] Python 3.9+ 已安装")
    print("   [ ] 所需 Python 包已安装 (pip install -r requirements.txt)")
    print("   [ ] Oracle Instant Client 已安装 (如需 Oracle 迁移)")
    print("   [ ] 环境变量已配置 (.env)")

    print("\n3. 迁移脚本:")
    print("   [ ] migrate_oracle_to_sqlite.py 配置正确 (Oracle → SQLite)")
    print("   [ ] migrate_oracle_to_oracle.py 配置正确 (Oracle → Oracle)")
    print("   [ ] 迁移目标目录有足够空间")

    print("\n4. 迁移后验证:")
    print("   [ ] 目标数据库数据已正确迁移")
    print("   [ ] 后端配置已修改为指向目标数据库")
    print("   [ ] 应用能正常启动")

def main():
    print("台账管理系统迁移环境检查")
    print("="*60)

    # 检查 Python 版本
    python_ok = check_python_version()

    # 检查必需包
    required_ok, optional_ok = check_required_packages()

    # 检查 Oracle
    oracle_ok = check_oracle_instant_client()

    # 检查 SQLite
    check_sqlite_file()

    # 显示检查清单
    show_migration_checklist()

    # 总结
    print("\n" + "="*60)
    print("检查结果总结:")
    print("="*60)

    if python_ok and required_ok:
        print("✓ 基本环境满足要求")

        if oracle_ok:
            print("✓ Oracle 环境已准备就绪")
            print("  可以执行 Oracle → SQLite 或 Oracle → Oracle 迁移")
        else:
            print("⚠ Oracle 环境未完全准备")
            print("  如需 Oracle 迁移，请先安装 Oracle Instant Client")
    else:
        print("✗ 基本环境不满足要求")
        print("  请先解决上述问题")

    print("\n下一步:")
    print("1. 如有环境问题，请先解决")
    print("2. 查看 MIGRATION_GUIDE.md 了解详细步骤")
    print("3. 执行相应的迁移脚本")

if __name__ == "__main__":
    main()