import re

# 读取文件
with open('app/api/api_v1/endpoints/ledgers.py', 'r') as f:
    content = f.read()

# 添加导入
if 'from urllib.parse import quote' not in content:
    content = re.sub(
        r'from datetime import datetime',
        'from datetime import datetime\nfrom urllib.parse import quote',
        content
    )

# 修改所有 Response 返回中的文件名编码
# 修改 xlsx 文件名
content = re.sub(
    r'filename = f"台账_\{ledger\.id\}_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.xlsx"\s+return Response\(',
    'filename = f"台账_{ledger.id}_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.xlsx"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)
content = re.sub(
    r'filename = f"台账_\{ledger\.id\}_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.csv"\s+return Response\(',
    'filename = f"台账_{ledger.id}_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.csv"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)
content = re.sub(
    r'filename = f"台账_\{ledger\.id\}_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.txt"\s+return Response\(',
    'filename = f"台账_{ledger.id}_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.txt"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)
content = re.sub(
    r'filename = f"台账列表_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.xlsx"\s+return Response\(',
    'filename = f"台账列表_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.xlsx"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)
content = re.sub(
    r'filename = f"台账列表_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.csv"\s+return Response\(',
    'filename = f"台账列表_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.csv"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)
content = re.sub(
    r'filename = f"台账列表_\{datetime\.now\(\)\.strftime\(\'%Y%m%d%H%M%S\'\)\}\.txt"\s+return Response\(',
    'filename = f"台账列表_{datetime.now().strftime(\'%Y%m%d%H%M%S\')}.txt"\n        encoded_filename = quote(filename)\n        return Response(',
    content
)

# 修改所有 Content-Disposition 头
content = re.sub(
    r'headers=\{"Content-Disposition": f"attachment; filename=\{filename\}"\}',
    'headers={"Content-Disposition": f"attachment; filename*=UTF-8\'\'{encoded_filename}"}',
    content
)

# 写入文件
with open('app/api/api_v1/endpoints/ledgers.py', 'w') as f:
    f.write(content)

print('文件已修改') 