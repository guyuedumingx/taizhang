import { api } from './index';
import { AutoFillTriggerConfig, AutoFillTriggerConfigCreate, AutoFillTriggerConfigUpdate, PaginatedResponse } from '../types';

export async function getAutoFillConfigs(skip = 0, limit = 100): Promise<PaginatedResponse<AutoFillTriggerConfig>> {
  const response = await api.get('/auto-fill-configs/', { params: { skip, limit } });
  return response.data;
}

export async function getAutoFillConfig(id: number): Promise<AutoFillTriggerConfig> {
  const response = await api.get(`/auto-fill-configs/${id}`);
  return response.data;
}

export async function createAutoFillConfig(data: AutoFillTriggerConfigCreate): Promise<AutoFillTriggerConfig> {
  const response = await api.post('/auto-fill-configs/', data);
  return response.data;
}

export async function updateAutoFillConfig(id: number, data: AutoFillTriggerConfigUpdate): Promise<AutoFillTriggerConfig> {
  const response = await api.put(`/auto-fill-configs/${id}`, data);
  return response.data;
}

export async function deleteAutoFillConfig(id: number): Promise<void> {
  await api.delete(`/auto-fill-configs/${id}`);
}
