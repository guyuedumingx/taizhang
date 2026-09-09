import { api } from './index';

// ---------- 导入配置 ----------

export interface ImportConfig {
  template_name: string;
  max_rows: number;
  warn_rows: number;
  max_rows_hard_limit: number;
  name_field?: string | null;
  unique_keys: string[];
  identity_mapping: Record<string, string>;
  field_order: string[];
}

export async function listImportConfigs() {
  const response = await api.get('/ledgers/import-configs');
  return response.data as { configs: ImportConfig[] };
}

export async function reloadImportConfigs() {
  const response = await api.post('/ledgers/import-configs/reload');
  return response.data as { message: string; count: number };
}

// ---------- 导入模板下载 ----------

export async function downloadImportTemplate(templateId: number) {
  const response = await api.get(`/ledgers/import-template/${templateId}`, {
    responseType: 'blob',
    headers: {
      Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
  });
  return response.data as Blob;
}

// ---------- 预校验 / 提交 ----------

export interface ImportIssue {
  row: number;
  type: string;
  field?: string | null;
  raw?: unknown;
  reason: string;
}

export interface CleanablePreview {
  row: number;
  field: string;
  raw: unknown;
  clean: unknown;
}

export interface ImportValidationReport {
  template_id: number;
  template_name: string;
  preview_batch_id: string;
  total_rows: number;
  importable_count: number;
  cleanable_count: number;
  issues: ImportIssue[];
  cleanable_previews: CleanablePreview[];
  row_limit_warning?: string | null;
}

export async function validateImport(
  templateId: number,
  file: File,
  teamId?: number,
) {
  const formData = new FormData();
  formData.append('template_id', String(templateId));
  formData.append('file', file);
  if (teamId !== undefined && teamId !== null) {
    formData.append('team_id', String(teamId));
  }
  const response = await api.post('/ledgers/import/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data as ImportValidationReport;
}

export interface ImportFailedItem {
  row: number;
  field?: string | null;
  raw?: unknown;
  reason: string;
}

export interface ImportCommitResult {
  batch_id: string;
  template_id: number;
  template_name: string;
  success_count: number;
  failed_count: number;
  elapsed_seconds: number;
  created_ledger_ids: number[];
  failed_items: ImportFailedItem[];
  failures_download_url?: string | null;
}

export async function commitImport(
  templateId: number,
  file: File,
  teamId?: number,
) {
  const formData = new FormData();
  formData.append('template_id', String(templateId));
  formData.append('file', file);
  if (teamId !== undefined && teamId !== null) {
    formData.append('team_id', String(teamId));
  }
  const response = await api.post('/ledgers/import/commit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data as ImportCommitResult;
}

// ---------- 导入历史 ----------

export interface ImportHistoryItem {
  batch_id: string;
  template_id: number;
  template_name: string;
  imported_by_id: number;
  imported_by_name?: string | null;
  imported_at: string;
  total_rows: number;
  success_count: number;
  failed_count: number;
  filename?: string | null;
}

export interface ImportHistoryList {
  total: number;
  items: ImportHistoryItem[];
}

export async function listImportHistory(skip = 0, limit = 20) {
  const response = await api.get(`/ledgers/import/history?skip=${skip}&limit=${limit}`);
  return response.data as ImportHistoryList;
}

export interface ImportHistoryDetail extends ImportHistoryItem {
  created_ledger_ids: number[];
  failed_items?: ImportFailedItem[] | null;
}

export async function getImportHistoryDetail(batchId: string) {
  const response = await api.get(`/ledgers/import/history/${batchId}`);
  return response.data as ImportHistoryDetail;
}

export async function downloadImportFailures(batchId: string) {
  const response = await api.get(`/ledgers/import/history/${batchId}/failures`, {
    responseType: 'blob',
    headers: {
      Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
  });
  return response.data as Blob;
}
