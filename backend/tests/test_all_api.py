import pytest
import importlib
import inspect
import os
import sys
from pathlib import Path

# 添加测试模块路径
TEST_API_DIR = Path(__file__).parent / "api"
sys.path.append(str(TEST_API_DIR))

# 导入所有测试模块
def import_all_test_modules():
    test_modules = []
    for file in os.listdir(TEST_API_DIR):
        if file.startswith("test_") and file.endswith(".py"):
            module_name = file[:-3]  # 移除 .py 后缀
            try:
                module = importlib.import_module(module_name)
                test_modules.append(module)
                print(f"成功导入测试模块: {module_name}")
            except ImportError as e:
                print(f"导入测试模块 {module_name} 失败: {e}")
    return test_modules

# 获取测试函数
def get_all_test_functions(modules):
    test_functions = []
    for module in modules:
        for name, obj in inspect.getmembers(module):
            if name.startswith("test_") and callable(obj):
                test_functions.append(obj)
                print(f"发现测试函数: {module.__name__}.{name}")
    return test_functions

# 执行所有测试
def run_all_tests():
    print("开始导入测试模块...")
    modules = import_all_test_modules()
    print(f"共导入 {len(modules)} 个测试模块")
    
    print("获取所有测试函数...")
    test_functions = get_all_test_functions(modules)
    print(f"共发现 {len(test_functions)} 个测试函数")
    
    print("开始执行测试...")
    success_count = 0
    failure_count = 0
    error_count = 0
    
    for func in test_functions:
        func_name = f"{func.__module__}.{func.__name__}"
        try:
            print(f"执行测试: {func_name}")
            func()
            success_count += 1
            print(f"测试通过: {func_name}")
        except AssertionError as e:
            failure_count += 1
            print(f"测试失败: {func_name} - {e}")
        except Exception as e:
            error_count += 1
            print(f"测试错误: {func_name} - {e}")
    
    print("\n===== 测试结果汇总 =====")
    print(f"总测试数: {len(test_functions)}")
    print(f"通过: {success_count}")
    print(f"失败: {failure_count}")
    print(f"错误: {error_count}")
    
    if failure_count == 0 and error_count == 0:
        print("✅ 所有测试通过!")
        return True
    else:
        print("❌ 部分测试未通过!")
        return False

if __name__ == "__main__":
    print("====================================")
    print("   开始测试所有后端API接口")
    print("====================================")
    
    success = run_all_tests()
    
    print("====================================")
    print("   测试结束")
    print("====================================")
    
    # 如果有测试失败，返回非零退出码
    if not success:
        sys.exit(1) 