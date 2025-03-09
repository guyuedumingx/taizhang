#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查数据库表结构

这个脚本用于检查数据库表结构，帮助调试模型与数据库不匹配的问题
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加当前目录到路径
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings

def check_db_schema():
    """检查数据库表结构"""
    print(f"数据库路径: {settings.SQLALCHEMY_DATABASE_URI}")
    
    # 从URI中提取数据库文件路径
    db_path = settings.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return
    
    print(f"连接到数据库: {db_path}")
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n发现 {len(tables)} 个表:")
    for table in tables:
        table_name = table[0]
        print(f"\n表: {table_name}")
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        print(f"  列数: {len(columns)}")
        for column in columns:
            col_id, col_name, col_type, not_null, default_value, is_pk = column
            print(f"  - {col_name} ({col_type}), 主键: {is_pk}, 非空: {not_null}, 默认值: {default_value}")
    
    # 关闭连接
    conn.close()

if __name__ == "__main__":
    check_db_schema() 