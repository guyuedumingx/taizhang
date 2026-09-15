// 统计分析视图（台账汇总查询保存的筛选组合）的存储与同步。
// 视图存 localStorage（个人级，绝对不建表约束下的形态）；
// 侧边菜单动态渲染这些视图，保存/删除后通过自定义事件通知菜单刷新。

export const VIEWS_STORAGE_KEY = "taizhang_ledger_query_views";
export const VIEWS_CHANGED_EVENT = "taizhang_ledger_query_views_changed";

export interface SavedViewFilters {
  selectedTemplateIds: number[];
  keyword: string;
  statusSel: string[];
  approvalSel: string[];
  teamIds: number[];
  creatorIds: number[];
  createdAtRange: [string, string] | null;
  fieldFilters: Record<string, { operator: string; value?: any }>;
  aggregations: { type: string; field?: string | null; label?: string | null }[];
}

export interface SavedView {
  name: string;
  saved_at: string;
  filters: SavedViewFilters;
}

export function loadSavedViews(): SavedView[] {
  try {
    const raw = localStorage.getItem(VIEWS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function persistSavedViews(views: SavedView[]) {
  localStorage.setItem(VIEWS_STORAGE_KEY, JSON.stringify(views));
  window.dispatchEvent(new Event(VIEWS_CHANGED_EVENT));
}

export function findSavedView(name: string): SavedView | undefined {
  return loadSavedViews().find((v) => v.name === name);
}
