"""
自动填充外部 API 调用与数据提取：从配置读取唯一外部系统，带 Token 请求，按 response_path 提取数据。
只做数据提取和基本格式化，不进行字段匹配和类型转换。
"""
from typing import Any, Dict, List, Optional

import httpx


def _replace_placeholder(obj: Any, value: str) -> Any:
    """递归替换占位符 {field_value}。"""
    if isinstance(obj, dict):
        return {k: _replace_placeholder(v, value) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_placeholder(item, value) for item in obj]
    if isinstance(obj, str):
        return obj.replace("{field_value}", value)
    return obj


def extract_response_data(response_data: Dict[str, Any], response_path: str) -> List[Dict[str, Any]]:
    """
    从响应中按 response_path 提取数据（支持点号分隔的嵌套路径）。
    返回列表；外部系统一般只返回 0 条或 1 条，调用方可取第一条。
    """
    if not response_path:
        if isinstance(response_data, list):
            return response_data
        if isinstance(response_data, dict):
            return [response_data]
        return []
    parts = response_path.split(".")
    current: Any = response_data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return []
    if isinstance(current, list):
        return current
    if isinstance(current, dict):
        return [current]
    return []


def call_external_api(
    system_config: Dict[str, Any],
    token: str,
    field_value: str,
) -> List[Dict[str, Any]]:
    """
    调用外部系统 API。使用 system_config 中的 URL、method、request_config，
    将 {field_value} 替换为 field_value，带 Bearer token 请求，按 response_path 提取数据。
    返回 0 条或 1 条记录（多条时只取第一条）。异常时抛出或返回空列表。
    """
    url = f"{system_config['api_base_url']}{system_config.get('api_endpoint', '')}"
    config = system_config.get("request_config", {})
    headers = {
        "Authorization": f"Bearer {token}",
        **config.get("headers", {}),
    }
    timeout = config.get("timeout", 5)
    retry_times = max(1, config.get("retry_times", 3))
    request_method = system_config.get("request_method", "GET").upper()

    last_error: Optional[Exception] = None
    for attempt in range(retry_times):
        try:
            with httpx.Client(timeout=timeout) as client:
                if request_method == "GET":
                    params = _replace_placeholder(config.get("params", {}), field_value)
                    response = client.get(url, params=params, headers=headers)
                elif request_method == "POST":
                    body = _replace_placeholder(config.get("body", {}), field_value)
                    response = client.post(url, json=body, headers=headers)
                else:
                    body = _replace_placeholder(config.get("body", {}), field_value)
                    response = client.request(request_method, url, json=body, headers=headers)
                response.raise_for_status()
                response_data = response.json()
                response_path = config.get("response_path", "")
                extracted = extract_response_data(response_data, response_path)
                if len(extracted) > 1:
                    extracted = [extracted[0]]
                return extracted
        except httpx.TimeoutException as e:
            last_error = e
            if attempt == retry_times - 1:
                raise ValueError("外部API请求超时") from e
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 401:
                raise ValueError("Token无效或已过期") from e
            if attempt == retry_times - 1:
                raise
        except Exception as e:
            last_error = e
            if attempt == retry_times - 1:
                raise
    return []
