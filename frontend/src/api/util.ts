// 定义查询参数类型
export type QueryParams = Record<string, string | number | boolean | undefined>;

// 构建查询参数
export const buildQueryParams = (params?: QueryParams): string => {
  if (!params) return '';
  
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
    .join('&');
  
  return query ? `?${query}` : '';
};