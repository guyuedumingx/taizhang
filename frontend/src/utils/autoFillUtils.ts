/**
 * 自动填充：将外部系统返回的 raw_data 按模板字段做字段映射与类型转换，
 * 得到表单可用的键值对。类型与格式与当前项目中 Field 类型及 LedgerForm 表单项约定一致。
 */
import type { Field } from '../types';
import dayjs, { Dayjs } from 'dayjs';

/**
 * 将 raw_data 按模板字段与可选 field_mapping 做匹配，并按字段类型转换后返回。
 * 用于自动填充时 form.setFieldsValue({ data: result })。
 */
export function matchAndConvertFields(
  rawData: Record<string, unknown>,
  templateFields: Field[],
  fieldMapping?: Record<string, string>
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of templateFields) {
    const externalFieldName = fieldMapping?.[field.name ?? ''] ?? field.name ?? '';
    if (externalFieldName === '' || !(externalFieldName in rawData)) continue;
    const rawValue = rawData[externalFieldName];
    const fieldType = (field.type ?? 'input').toLowerCase();
    switch (fieldType) {
      case 'input':
      case 'textarea':
        result[field.name ?? ''] = rawValue != null ? String(rawValue) : '';
        break;
      case 'number':
        if (rawValue == null || rawValue === '') {
          result[field.name ?? ''] = undefined;
        } else {
          const n = Number(rawValue);
          result[field.name ?? ''] = Number.isNaN(n) ? rawValue : n;
        }
        break;
      case 'date':
        result[field.name ?? ''] = formatDateForForm(rawValue, 'date');
        break;
      case 'datetime':
        result[field.name ?? ''] = formatDateForForm(rawValue, 'datetime');
        break;
      case 'select':
      case 'radio':
        const strVal = rawValue != null ? String(rawValue) : '';
        if (field.options && field.options.length && field.options.includes(strVal)) {
          result[field.name ?? ''] = strVal;
        }
        break;
      case 'checkbox':
        result[field.name ?? ''] = Array.isArray(rawValue) ? rawValue : rawValue != null ? [rawValue] : [];
        break;
      default:
        result[field.name ?? ''] = rawValue;
    }
  }
  return result;
}

/**
 * 将外部系统的日期/日期时间转为表单可用的值。
 * LedgerForm 中 date 使用 DatePicker（Ant Design 5 使用 dayjs），datetime 未单独实现时按字符串。
 */
function formatDateForForm(
  dateValue: unknown,
  kind: 'date' | 'datetime'
): string | Dayjs | undefined {
  if (dateValue == null || dateValue === '') return undefined;
  const date = dayjs(dateValue as string | number | Date);
  if (!date.isValid()) return typeof dateValue === 'string' ? dateValue : String(dateValue);
  if (kind === 'date') {
    return date; // dayjs 对象供 DatePicker 使用
  }
  return date.format('YYYY-MM-DD HH:mm:ss');
}
