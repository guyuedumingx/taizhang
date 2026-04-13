import { api } from './index';

export interface AutoFillResponse {
  success: boolean;
  matched: boolean;
  raw_data?: Record<string, unknown>;
  message?: string;
}

/**
 * 调用自动填充接口：根据字段名查找全局配置的 API，用字段值请求并返回匹配数据。
 */
export async function autoFill(
  templateId: number,
  fieldName: string,
  fieldValue: string
): Promise<AutoFillResponse> {
  const response = await api.post<AutoFillResponse>(
    `/templates/${templateId}/auto-fill`,
    { field_name: fieldName, field_value: fieldValue }
  );
  return response.data;
}
