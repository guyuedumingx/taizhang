import { api } from './index';
import { LedgerQueryResponse, QueryField, StatisticsQueryRequest } from '../types';

// 多维度台账汇总查询
export async function ledgerQuery(payload: StatisticsQueryRequest): Promise<LedgerQueryResponse> {
  const response = await api.post('/statistics/ledger-query', payload);
  return response.data;
}

// 获取指定模板的字段列表（动态筛选条件用）
export async function getQueryFields(templateId: number): Promise<QueryField[]> {
  const response = await api.get('/statistics/query-fields', { params: { template_id: templateId } });
  return response.data;
}

// 导出查询结果为 Excel（清洗后值 + 可疑数据 Sheet）
export async function exportLedgerQuery(payload: StatisticsQueryRequest): Promise<Blob> {
  const response = await api.post('/statistics/export', payload, { responseType: 'blob' });
  return response.data;
}
