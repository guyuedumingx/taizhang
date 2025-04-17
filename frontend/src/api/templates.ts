import { api } from './index';
import { Template, TemplateDetail, TemplateCreate, TemplateUpdate, Field, FieldCreate, FieldUpdate } from '../types';
import { QueryParams, buildQueryParams } from './util';

// 获取模板列表
export async function getTemplates(params?: QueryParams): Promise<Template[]> {
  const query = buildQueryParams(params);
  const response = await api.get(`/templates/${query}`);
  return response.data;
}

// 获取模板详情
export async function getTemplate(id: number): Promise<Template> {
  const response = await api.get(`/templates/${id}`);
  return response.data;
}

// 获取模板详情（包含字段）
export async function getTemplateDetail(id: number): Promise<TemplateDetail> {
  const response = await api.get(`/templates/${id}`);
  return response.data;
}

// 创建模板
export async function createTemplate(data: TemplateCreate): Promise<Template> {
  const response = await api.post('/templates/', data);
  return response.data;
}

// 更新模板
export async function updateTemplate(id: number, data: TemplateUpdate): Promise<Template> {
  const response = await api.put(`/templates/${id}`, data);
  return response.data;
}

// 删除模板
export async function deleteTemplate(id: number): Promise<Template> {
  const response = await api.delete(`/templates/${id}`);
  return response.data;
}

// 获取模板字段
export async function getTemplateFields(id: number): Promise<Field[]> {
  const response = await api.get(`/templates/${id}/fields`);
  return response.data;
}

// 创建模板字段
export async function createField(templateId: number, data: FieldCreate): Promise<Field> {
  const response = await api.post(`/templates/${templateId}/fields`, data);
  return response.data;
}

// 更新模板字段
export async function updateField(templateId: number, fieldId: number, data: FieldUpdate): Promise<Field> {
  const response = await api.put(`/templates/${templateId}/fields/${fieldId}`, data);
  return response.data;
}

// 删除模板字段
export async function deleteField(templateId: number, fieldId: number): Promise<Field> {
  const response = await api.delete(`/templates/${templateId}/fields/${fieldId}`);
  return response.data;
} 