"""
自动填充外部 API 调用：根据模板配置的 api_url 和 headers，POST JSON body，返回响应数据。
"""
from typing import Any, Dict, Optional

import httpx


def call_external_api(
    api_url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    timeout: int = 5,
    retry_times: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    调用外部 API，POST JSON body，返回响应中的第一条数据。
    超时或异常时抛出 ValueError。
    """
    last_error: Optional[Exception] = None
    for attempt in range(retry_times):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(api_url, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
                # 如果返回列表，取第一条
                if isinstance(data, list):
                    return data[0] if data else None
                if isinstance(data, dict):
                    return data
                return None
        except httpx.TimeoutException as e:
            last_error = e
            if attempt == retry_times - 1:
                raise ValueError("外部API请求超时") from e
        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt == retry_times - 1:
                raise ValueError(f"外部API返回错误: {e.response.status_code}") from e
        except Exception as e:
            last_error = e
            if attempt == retry_times - 1:
                raise ValueError(f"外部API调用失败: {str(e)}") from e
    return None
