import api from '../api';
import { Template, TemplateDetail, TemplateCreate, TemplateUpdate, Field, FieldCreate, FieldUpdate } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class TemplateService {
  // 获取模板列表
  static async getTemplates(params?: QueryParams): Promise<Template[]> {
    try {
      const response = await api.templates.getTemplates(params);
      console.log('Templates API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取templates数组');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error('API返回的templates格式不正确:', response);
      return [];
    } catch (error) {
      console.error('获取模板列表失败:', error);
      throw error;
    }
  }

  // 获取模板详情
  static async getTemplate(id: number): Promise<Template> {
    try {
      return await api.templates.getTemplate(id);
    } catch (error) {
      console.error(`获取模板 ${id} 详情失败:`, error);
      throw error;
    }
  }

  // 获取模板详情（包含字段）
  static async getTemplateDetail(id: number): Promise<TemplateDetail> {
    try {
      return await api.templates.getTemplateDetail(id);
    } catch (error) {
      console.error(`获取模板 ${id} 详情（包含字段）失败:`, error);
      throw error;
    }
  }

  // 创建模板
  static async createTemplate(data: TemplateCreate): Promise<Template> {
    try {
      return await api.templates.createTemplate(data);
    } catch (error) {
      console.error('创建模板失败:', error);
      throw error;
    }
  }

  // 更新模板
  static async updateTemplate(id: number, data: TemplateUpdate): Promise<Template> {
    try {
      return await api.templates.updateTemplate(id, data);
    } catch (error) {
      console.error(`更新模板 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除模板
  static async deleteTemplate(id: number): Promise<void> {
    try {
      await api.templates.deleteTemplate(id);
    } catch (error) {
      console.error(`删除模板 ${id} 失败:`, error);
      throw error;
    }
  }

  // 获取模板字段列表
  static async getTemplateFields(templateId: number): Promise<Field[]> {
    try {
      const response = await api.templates.getTemplateFields(templateId);
      console.log(`获取模板 ${templateId} 字段列表返回数据:`, response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log(`从分页数据中提取模板 ${templateId} 字段数组`);
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error(`获取模板 ${templateId} 字段列表返回格式不正确:`, response);
      return [];
    } catch (error) {
      console.error(`获取模板 ${templateId} 字段列表失败:`, error);
      throw error;
    }
  }

  // 创建字段
  static async createField(templateId: number, data: FieldCreate): Promise<Field> {
    try {
      return await api.templates.createField(templateId, data);
    } catch (error) {
      console.error(`为模板 ${templateId} 创建字段失败:`, error);
      throw error;
    }
  }

  // 更新字段
  static async updateField(templateId: number, fieldId: number, data: FieldUpdate): Promise<Field> {
    try {
      return await api.templates.updateField(templateId, fieldId, data);
    } catch (error) {
      console.error(`更新字段 ${fieldId} 失败:`, error);
      throw error;
    }
  }

  // 删除字段
  static async deleteField(templateId: number, fieldId: number): Promise<void> {
    try {
      await api.templates.deleteField(templateId, fieldId);
    } catch (error) {
      console.error(`删除字段 ${fieldId} 失败:`, error);
      throw error;
    }
  }
} 