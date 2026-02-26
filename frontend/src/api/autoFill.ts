import { api } from './index';

export interface AutoFillResponse {
  success: boolean;
  matched: boolean;
  raw_data?: Record<string, unknown>;
  source?: { system_name: string; external_id?: string };
  message?: string;
}

/**
 * 调用自动填充接口：根据关键字段值从外部系统查询并返回原始数据。
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
