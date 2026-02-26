# 自动填充功能测试方案

本文说明如何从零到完整验证自动填充功能，不执行测试，仅提供可照做的步骤。

---

## 一、环境准备

### 1.1 数据库迁移

在 **backend** 目录下、已激活项目虚拟环境时执行：

```bash
cd backend
python -m app.db.migrate_auto_fill_config
```

预期：终端输出 `Added column templates.auto_fill_config (SQLite).` 或 `Column auto_fill_config already exists, skip.`。

### 1.2 后端配置

在 `backend/.env`（或系统环境变量）中配置自动填充相关项。分两种测试方式：

- **方式 A：对接真实外部系统**  
  按你真实 API 的地址、路径、请求方式、响应结构填写下面配置。

- **方式 B：用本地 Mock 服务模拟外部系统**  
  先按下面「二、Mock 外部系统」起一个假接口，再把这些配置指向该 Mock。

最小必填项示例（GET 请求、占位符 `{field_value}`）：

```env
# 启用自动填充
AUTO_FILL_ENABLED=true

# 外部系统 base 地址（Mock 时用 http://127.0.0.1:端口）
AUTO_FILL_API_BASE_URL=http://127.0.0.1:9999
AUTO_FILL_REQUEST_METHOD=GET

# 请求路径（可带查询参数，占位符为 {field_value}）
AUTO_FILL_API_ENDPOINT=/api/search?code={field_value}

# request_config：JSON 字符串，包含 response_path、timeout、params 等
# 若 GET 参数已在 ENDPOINT 里写死，这里可只配 response_path 和 timeout
AUTO_FILL_REQUEST_CONFIG_JSON={"response_path":"data.items","timeout":5,"retry_times":2}

# 可选：外部系统展示名称
AUTO_FILL_EXTERNAL_SYSTEM_NAME=测试外部系统

# 可选：备用 Token 对应用户号（当前用户无 Token 时用该用户的 Token）
# AUTO_FILL_BACKUP_TOKEN_USER_ID=backup_user
```

若外部为 **POST**，且 body 里要替换 `{field_value}`，可例如：

```env
AUTO_FILL_REQUEST_METHOD=POST
AUTO_FILL_API_ENDPOINT=/api/search
AUTO_FILL_REQUEST_CONFIG_JSON={"response_path":"data.list","timeout":5,"body":{"keyword":"{field_value}"},"headers":{"Content-Type":"application/json"}}
```

配置完成后重启后端服务。

---

## 二、Mock 外部系统（无真实系统时）

无真实外部 API 时，可用本地 Mock 服务模拟「按关键字段查询并返回一条数据」。

### 2.1 用 Python 起一个简单 Mock（推荐）

新建文件 `backend/scripts/mock_external_api.py`（或任意目录），内容示例：

```python
# 保存为 mock_external_api.py，运行：python mock_external_api.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

PORT = 9999

class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        # 假设前端传的是 code=xxx
        code = (qs.get("code") or [""])[0]
        # 模拟：根据 code 返回一条数据，没有则空列表
        if len(code.strip()) >= 2:
            items = [{
                "id": "ext-001",
                "device_name": "Mock设备",
                "device_model": "M-2024",
                "supplier": "Mock供应商",
                "purchase_date": "2024-01-01T00:00:00Z",
            }]
        else:
            items = []
        body = json.dumps({"data": {"items": items}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print("[Mock]", args[0])

HTTPServer(("", PORT), MockHandler).serve_forever()
```

运行：`python mock_external_api.py`，保持终端不关。此时 Mock 地址为 `http://127.0.0.1:9999`，上面 `.env` 中的 `AUTO_FILL_API_BASE_URL` 和 `AUTO_FILL_API_ENDPOINT` 需与之匹配，例如：

- `AUTO_FILL_API_BASE_URL=http://127.0.0.1:9999`
- `AUTO_FILL_API_ENDPOINT=/api/search` 且 Mock 里改 `self.path == "/api/search"`，或在 request_config 里用 `params: {"code": "{field_value}"}`，Mock 读 `code` 参数。

若 Mock 写在根路径，可设 `AUTO_FILL_API_ENDPOINT=/`，并在 Mock 里解析 query 的 `code`。

### 2.2 与 request_config 的对应关系

- Mock 返回格式需与 `AUTO_FILL_REQUEST_CONFIG_JSON` 里的 `response_path` 一致。  
  上面示例返回 `{"data": {"items": [...]}}`，则 `response_path` 应为 `data.items`。
- GET 时：若 `ENDPOINT` 已带 `?code={field_value}`，request_config 可不写 `params`；若 ENDPOINT 只有路径，则在 request_config 里写 `"params": {"code": "{field_value}"}`。

---

## 三、接口测试步骤

以下用 curl 示例，也可用 Postman/Apifox 等。

### 3.1 获取登录 Token（台账系统）

用已在系统里的用户登录，拿到 JWT：

```bash
curl -s -X POST "http://<后端地址>/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=你的用户名&password=你的密码"
```

记下返回里的 `access_token`，后续请求自动填充接口时需带在 Header：`Authorization: Bearer <access_token>`。

### 3.2 接收 Token 接口（写入缓存）

把「用户号」和「外部系统用的 Token」写入台账后端缓存（无真实外部 Token 时，Mock 可不需要鉴权，这里随便写一个字符串即可）：

```bash
curl -X POST "http://<后端地址>/api/v1/auto-fill/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"1","token":"mock-token-123"}'
```

- `user_id` 建议与台账系统当前登录用户 ID 一致（如登录用户 id=1 则填 `"1"`），这样自动填充时会优先用该用户的 Token。
- 预期响应：`{"success":true,"message":"Token已接收并缓存"}`。

### 3.3 准备模板与自动填充配置

1. 在系统中创建一个模板（或选已有模板），并为该模板**增加/编辑**自动填充配置（`auto_fill_config`）。
2. 配置需包含且与 Mock/真实接口一致：
   - `enabled: true`
   - `key_field_name`：与模板中某一字段的 **name** 完全一致（如 `设备编号` 或英文名）。
   - `min_field_length`：如 `2`（触发自动填充的最小长度）。
3. 若 Mock 返回的字段名与模板字段名不一致，在模板的 `auto_fill_config.field_mapping` 里配置「外部字段名 -> 模板字段名」映射。

可通过「模板管理」的编辑接口提交上述 JSON，或直接在数据库里给该模板的 `auto_fill_config` 列写入相应 JSON。

### 3.4 自动填充接口

用 3.1 的 JWT、3.2 的 user_id 对应账号，调用：

```bash
curl -X POST "http://<后端地址>/api/v1/templates/<template_id>/auto-fill" \
  -H "Authorization: Bearer <上一步的 access_token>" \
  -H "Content-Type: application/json" \
  -d '{"field_name":"<key_field_name>","field_value":"ab"}'
```

- `template_id`：已配置自动填充的模板 ID。
- `field_name`：与模板里 `key_field_name` 一致。
- `field_value`：长度 ≥ 模板里配置的 `min_field_length`（如 2）。

预期（Mock 有数据时）：  
`{"success":true,"matched":true,"raw_data":{...},"source":{...}}`  

若未配置 Token 或未启用自动填充等，会返回 400/503/502，根据 message 检查配置与 Token 是否已写入。

---

## 四、前端联调测试步骤

1. **启动**：后端 + Mock（若用）+ 前端 dev 服务。
2. **登录**：用已在「接收 Token 接口」中配置过 `user_id` 的账号登录（如 id=1）。
3. **创建台账**：进入「创建台账」，选择已配置自动填充的模板。
4. **触发自动填充**：  
   - 找到与 `key_field_name` 对应的表单项（如「设备编号」）。  
   - 输入不少于 `min_field_length` 个字符（如 `ab`），然后：  
     - **失焦**：点击其他控件，应触发一次请求；或  
     - **停止输入**：保持在该输入框，停止输入约 2 秒，再触发一次请求。
5. **预期**：  
   - 请求成功且外部返回一条数据时：其他映射好的字段应被自动填好，并可能有「已自动填充」提示。  
   - 无数据时：可能有「未找到匹配记录」类提示。  
   - 网络/Token/配置错误时：有错误提示，可根据接口返回的 message 排查。

可选验证：

- 打开浏览器开发者工具 Network，筛选 XHR，确认请求 `POST .../templates/<id>/auto-fill` 的请求体、响应与预期一致。
- 换一个未在「接收 Token」里配置过的用户登录，预期自动填充因「未找到可用 Token」而失败（或走备用 Token，若你配置了 `AUTO_FILL_BACKUP_TOKEN_USER_ID` 并为该用户写了 Token）。

---

## 五、测试检查清单（自检用）

| 项目 | 说明 |
|------|------|
| 迁移 | 已执行 `python -m app.db.migrate_auto_fill_config`，无报错 |
| 配置 | `.env` 中 `AUTO_FILL_ENABLED`、`AUTO_FILL_API_BASE_URL`、`AUTO_FILL_API_ENDPOINT`、`AUTO_FILL_REQUEST_CONFIG_JSON` 已填且与 Mock/真实 API 一致 |
| Mock（若用） | Mock 服务已启动，URL、路径、query/body、返回结构与 request_config 的 params/body、response_path 一致 |
| 接收 Token | `POST /api/v1/auto-fill/token` 返回 success，且 user_id 与待测登录用户 id 一致 |
| 模板配置 | 模板的 `auto_fill_config.enabled=true`，`key_field_name` 与模板字段 name 一致，`min_field_length` 合理 |
| 自动填充接口 | 用该用户 JWT 调 `POST .../templates/<id>/auto-fill`，field_name/value 符合要求时返回 matched 与 raw_data |
| 前端 | 关键字段失焦或停止输入约 2 秒后发起请求，且成功时其他字段被正确填充 |

---

## 六、可选：自动化测试思路

- **后端单测**：  
  - 对 `get_token_for_auto_fill`、`extract_response_data`、`call_external_api`（可 mock httpx）写单元测试。  
  - 对 `POST /api/v1/auto-fill/token` 和 `POST /api/v1/templates/<id>/auto-fill` 写接口测试（mock DB 与外部 HTTP），验证 400/503/200 及返回结构。
- **前端**：  
  - 对 `matchAndConvertFields` 写单测，覆盖各字段类型与 field_mapping。  
  - E2E（如 Playwright）：登录 -> 选模板 -> 输入关键字段 -> 断言请求与表单被填充。

按上述步骤即可在不执行测试的前提下，自行完成从环境准备到接口、前端的完整验证。
