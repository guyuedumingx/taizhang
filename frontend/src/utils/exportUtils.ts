import * as XLSX from 'xlsx';
import { Ledger, Template, Field } from '../types';
import { LedgerService } from '../services/LedgerService';
import { TemplateService } from '../services/TemplateService';

// 字段接口，用于统一系统字段和自定义字段
interface GenericField {
  name: string;
  label: string;
  type?: string;
}

/**
 * 按模板导出台账到Excel
 * @param ledgers 台账数据
 * @param templates 模板数据
 * @param filename 导出文件名
 */
export const exportLedgersToExcel = async (
  ledgers: Ledger[],
  templates: Template[],
  filename: string = '台账导出.xlsx'
): Promise<void> => {
  try {
    // 创建一个新的工作簿
    const workbook = XLSX.utils.book_new();
    
    // 按模板分组台账数据
    const ledgersByTemplate = groupLedgersByTemplate(ledgers);
    
    // 为每个模板创建工作表
    for (const templateId in ledgersByTemplate) {
      const template = templates.find(t => t.id === Number(templateId));
      if (!template) continue;
      
      // 获取模板字段
      let templateFields: Field[] = [];
      try {
        const templateDetail = await TemplateService.getTemplateDetail(Number(templateId));
        templateFields = templateDetail.fields || [];
      } catch (error) {
        console.error(`获取模板 ${templateId} 字段失败:`, error);
      }
      
      // 生成工作表数据
      const sheetData = generateSheetData(ledgersByTemplate[templateId], templateFields);
      
      // 创建工作表
      const sheetName = template.name || `模板${templateId}`;
      const worksheet = XLSX.utils.aoa_to_sheet(sheetData);
      
      // 添加到工作簿
      XLSX.utils.book_append_sheet(workbook, worksheet, sheetName.slice(0, 31)); // Excel工作表名称最大长度为31个字符
    }
    
    // 导出Excel文件
    XLSX.writeFile(workbook, filename);
  } catch (error) {
    console.error('导出Excel失败:', error);
    throw error;
  }
};

/**
 * 按模板分组台账数据
 * @param ledgers 台账数据
 * @returns 分组后的台账数据
 */
const groupLedgersByTemplate = (ledgers: Ledger[]): Record<string, Ledger[]> => {
  const result: Record<string, Ledger[]> = {};
  
  for (const ledger of ledgers) {
    if (ledger.template_id) {
      const templateId = String(ledger.template_id);
      if (!result[templateId]) {
        result[templateId] = [];
      }
      result[templateId].push(ledger);
    }
  }
  
  return result;
};

/**
 * 生成工作表数据
 * @param ledgers 台账数据
 * @param fields 字段定义
 * @returns 工作表数据
 */
const generateSheetData = (ledgers: Ledger[], fields: Field[]): Array<Array<string>> => {
  // 定义系统默认字段
  const systemFields: GenericField[] = [
    { name: 'name', label: '台账名称' },
    { name: 'description', label: '描述' },
    { name: 'status', label: '状态' },
    { name: 'team_name', label: '团队' },
    { name: 'created_by_name', label: '创建人' },
    { name: 'created_at', label: '创建时间' },
    { name: 'updated_at', label: '更新时间' },
  ];
  
  // 合并系统字段和自定义字段
  const allFields: Array<GenericField | Field> = [...systemFields, ...fields];
  
  // 生成表头
  const header: string[] = allFields.map(field => field.label || field.name || '');
  
  // 生成表格数据
  const rows: Array<Array<string>> = ledgers.map(ledger => {
    return allFields.map(field => {
      // 处理系统字段
      if (field.name === 'created_at' || field.name === 'updated_at') {
        const dateValue = ledger[field.name as keyof Ledger];
        return dateValue ? new Date(dateValue as string).toLocaleString() : '';
      }
      
      // 处理普通系统字段
      if (systemFields.some(sf => sf.name === field.name)) {
        return String(ledger[field.name as keyof Ledger] || '');
      }
      
      // 处理自定义字段
      const customField = field as Field;
      if (!customField.name || customField.name === '') {
        return '';
      }
      
      const value = ledger.data[customField.name];
      
      // 根据字段类型处理值
      if (customField.type === 'checkbox' && Array.isArray(value)) {
        return value.join(', ');
      } else if (customField.type === 'date' && value) {
        return new Date(value as string).toLocaleDateString();
      } else if (value === null || value === undefined) {
        return '';
      }
      
      return String(value);
    });
  });
  
  // 合并表头和数据
  return [header, ...rows];
};

/**
 * 导出指定模板的所有台账
 * @param templateId 模板ID
 * @param filename 导出文件名
 */
export const exportTemplateAllLedgers = async (
  templateId: number,
  filename?: string
): Promise<void> => {
  try {
    // 获取模板详情
    const template = await TemplateService.getTemplateDetail(templateId);
    if (!template) {
      throw new Error(`未找到模板: ${templateId}`);
    }
    
    // 查询该模板下的所有台账
    const ledgers = await LedgerService.getLedgersByTemplate(templateId);
    
    // 设置导出文件名
    const exportFilename = filename || `${template.name}_台账导出.xlsx`;
    
    // 导出到Excel
    await exportLedgersToExcel(ledgers, [template], exportFilename);
    
    return Promise.resolve();
  } catch (error) {
    console.error('导出模板台账失败:', error);
    throw error;
  }
};

/**
 * 从Blob创建并下载文件
 * @param blob 文件Blob对象
 * @param filename 文件名
 */
export const downloadBlobAsFile = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

/**
 * 通过API导出台账
 * @param format 导出格式 ('excel', 'csv', 'txt')
 * @param templateId 模板ID
 * @returns 下载文件名
 */
export const exportLedgersViaAPI = async (
  format: string,
  templateId?: number
): Promise<string> => {
  try {
    // 确保格式有效
    const safeFormat = format.toLowerCase();
    if (!['excel', 'csv', 'txt'].includes(safeFormat)) {
      throw new Error(`不支持的导出格式: ${format}`);
    }
    
    // 获取文件扩展名
    const extension = safeFormat === 'excel' ? 'xlsx' : safeFormat;
    
    // 生成文件名
    let filename = `台账导出.${extension}`;
    
    // 如果指定了模板ID，先获取模板名称
    if (templateId) {
      try {
        const template = await TemplateService.getTemplateDetail(templateId);
        if (template) {
          filename = `${template.name}_台账导出.${extension}`;
        }
      } catch (error) {
        console.error('获取模板详情失败:', error);
      }
    }
    
    // 调用API导出
    const blob = await LedgerService.exportAllLedgers(safeFormat, templateId);
    
    // 下载文件
    downloadBlobAsFile(blob, filename);
    
    return filename;
  } catch (error) {
    console.error('通过API导出台账失败:', error);
    throw error;
  }
}; 