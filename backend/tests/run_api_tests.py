#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API测试运行器

这个脚本用于运行后端API的功能测试，可以测试单个API或所有API
"""

import os
import sys
import argparse
import importlib
import inspect
from pathlib import Path

# 添加当前目录到路径，确保可以导入测试模块
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

API_TEST_DIR = Path(__file__).parent / "api"

def list_available_tests():
    """列出所有可用的API测试"""
    tests = []
    for file in os.listdir(API_TEST_DIR):
        if file.startswith("test_") and file.endswith(".py"):
            module_name = file[:-3]  # 移除 .py 后缀
            tests.append(module_name)
    
    return tests

def run_test_module(module_name):
    """运行指定的测试模块"""
    try:
        print(f"\n{'=' * 60}")
        print(f"  开始运行测试: {module_name}")
        print(f"{'=' * 60}\n")
        
        # 导入测试模块
        full_module_name = f"api.{module_name}"
        module = importlib.import_module(full_module_name)
        
        # 获取所有测试函数
        test_functions = []
        for name, obj in inspect.getmembers(module):
            if name.startswith("test_") and callable(obj):
                test_functions.append((name, obj))
        
        # 如果模块有主函数，则直接调用
        if hasattr(module, "__main__") and module.__name__ == "__main__":
            module.__main__()
            return True
        
        # 否则依次执行测试函数
        success_count = 0
        failure_count = 0
        
        for name, func in test_functions:
            try:
                print(f"\n--- 执行测试: {name} ---\n")
                func()
                success_count += 1
                print(f"\n✅ 测试通过: {name}")
            except Exception as e:
                failure_count += 1
                print(f"\n❌ 测试失败: {name} - {e}")
        
        print(f"\n{'=' * 60}")
        print(f"  测试完成: {module_name}")
        print(f"  通过: {success_count}/{len(test_functions)}, 失败: {failure_count}/{len(test_functions)}")
        print(f"{'=' * 60}\n")
        
        return failure_count == 0
    except Exception as e:
        print(f"❌ 运行测试模块 {module_name} 时出错: {e}")
        return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="后端API测试运行器")
    
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="列出所有可用的测试"
    )
    
    parser.add_argument(
        "--run", 
        type=str,
        help="运行指定的测试，例如：--run test_workflows 或 --run all 运行所有测试"
    )
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 列出所有可用的测试
    available_tests = list_available_tests()
    
    if args.list:
        print("\n可用的API测试：")
        for i, test in enumerate(available_tests):
            print(f"{i+1}. {test}")
        print()
        return
    
    # 运行测试
    if args.run:
        if args.run == "all":
            # 运行所有测试
            print(f"\n{'=' * 60}")
            print(f"  开始运行所有API测试")
            print(f"{'=' * 60}\n")
            
            success_count = 0
            failure_count = 0
            
            for test in available_tests:
                if run_test_module(test):
                    success_count += 1
                else:
                    failure_count += 1
            
            print(f"\n{'=' * 60}")
            print(f"  所有API测试完成")
            print(f"  通过: {success_count}/{len(available_tests)}, 失败: {failure_count}/{len(available_tests)}")
            print(f"{'=' * 60}\n")
            
            # 返回非零退出码，如果有测试失败
            if failure_count > 0:
                sys.exit(1)
        else:
            # 运行指定的测试
            if args.run not in available_tests and args.run + ".py" not in os.listdir(API_TEST_DIR):
                print(f"❌ 错误: 找不到测试 '{args.run}'")
                print("可用的测试:")
                for test in available_tests:
                    print(f"  - {test}")
                sys.exit(1)
            
            # 去除.py后缀（如果有）
            test_name = args.run.replace(".py", "")
            if not run_test_module(test_name):
                sys.exit(1)
    else:
        # 如果没有指定操作，显示帮助信息
        print("请指定要执行的操作。使用 --help 查看帮助信息。")
        print("例子:")
        print("  python tests/run_api_tests.py --list")
        print("  python tests/run_api_tests.py --run test_workflows")
        print("  python tests/run_api_tests.py --run all")

if __name__ == "__main__":
    main() 