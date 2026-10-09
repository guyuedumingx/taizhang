/**
 * portrait 前端 API 封装 (P5 阶段, 批次 9)
 *
 * 对应后端 P4 18 端点 + /me/permissions (P5 共 19 端点暴露给前端).
 * MVP 范围: profile 查改 / submission 列表+详情+撤回 / approval 待审批+approve+reject+transfer.
 *
 * 集成指南 §5 雷区合规:
 *   - 7. 不绕过 Depends — 永远走 api (axios) + Bearer token
 *   - 6. 不改 approval_status 枚举 — 后端 portrait status 是 String, 前端只展示不解释
 */
import { api } from './index';

// ============================================================================
// 类型定义
// ============================================================================
export interface PortraitPermissions {
  user_id: number;
  ehr_id: string;
  is_admin: boolean;
  is_leader: boolean;
  is_user: boolean;
  permissions: {
    portrait_all: string[];
    portrait_self: string[];
    portrait_group: string[];
  };
}

export interface ProfileBase {
  id: number;
  user_id: number;
  gender?: string | null;
  nation?: string | null;
  birth_date?: string | null;
  job_title?: string | null;
  id_type?: string | null;
  id_number?: string | null;
  native_place?: string | null;
  birth_place?: string | null;
  household_place?: string | null;
  work_start_date?: string | null;
  hire_date?: string | null;
  marital_status?: string | null;
  is_emergency_staff: boolean;
  created_at: string;
  updated_at: string;
}

export interface PoliticalInfo {
  id?: number;
  profile_id?: number;
  political_status?: string | null;
  join_date?: string | null;
  introducer?: string | null;
}

export interface EducationInfo {
  id?: number;
  profile_id?: number;
  education_category?: string | null;
  education_type?: string | null;
  education_level?: string | null;
  degree?: string | null;
  school?: string | null;
  major_name?: string | null;
  duration_years?: string | null;
}

export interface FamilyInfo {
  id?: number;
  profile_id?: number;
  member_name?: string | null;
  relationship?: string | null;
  birth_date?: string | null;
  political_status?: string | null;
  work_unit?: string | null;
  job_title?: string | null;
  contact_phone?: string | null;
}

export interface ContactInfo {
  id?: number;
  profile_id?: number;
  mobile?: string | null;
  email?: string | null;
  address?: string | null;
  emergency_contact?: string | null;
  emergency_phone?: string | null;
}

export interface ProfileFull extends ProfileBase {
  user_name?: string | null;
  ehr_id?: string | null;
  department?: string | null;
  political?: PoliticalInfo | null;
  education?: EducationInfo | null;
  family?: FamilyInfo | null;
  contact?: ContactInfo | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface SubmissionRecord {
  id: number;
  submission_type: 'special_work' | 'profile_edit' | 'skill_tag_edit';
  submitter_user_id: number;
  submitter_name: string;
  submitter_ehr_id: string;
  workflow_instance_id?: number | null;
  current_approver_id?: number | null;
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'cancelled';
  payload?: any;  // DB 存的是 JSON 字符串, 后端不反序列化
  submitted_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  current_approver_name?: string | null;
  approval_count?: number;
  synced_ledger_id?: number | null;  // P8: special_work 审批通过后联动到的 ledger id
}

export interface ApprovalRecord {
  id: number;
  submission_id: number;
  approver_id: number;
  approver_name?: string | null;
  action: 'submit' | 'approve' | 'reject' | 'transfer' | 'withdraw';
  comment?: string | null;
  transferred_to_id?: number | null;
  created_at: string;
}

export interface SubmissionDetail extends SubmissionRecord {
  approvals: ApprovalRecord[];
}

export interface ApprovalActionResponse {
  success: boolean;
  message: string;
  submission?: SubmissionRecord;
}

// 用于审批人下拉的简化 User (后端 /users 返回 items 含完整字段, 这里只取必要 3 项)
export interface ApproverUser {
  id: number;
  name: string;
  ehr_id: string;
}

// ============================================================================
// 健康检查 + 权限
// ============================================================================
export async function getHealth(): Promise<{ status: string; module: string }> {
  const response = await api.get('/portrait/health');
  return response.data;
}

export async function getMyPermissions(): Promise<PortraitPermissions> {
  const response = await api.get('/portrait/me/permissions');
  return response.data;
}

// ============================================================================
// Profile (8 端点)
// ============================================================================
export async function getMyProfile(): Promise<ProfileFull> {
  const response = await api.get('/portrait/profiles/me');
  return response.data;
}

export async function getProfileByEhr(ehrId: string): Promise<ProfileFull> {
  const response = await api.get(`/portrait/profiles/${ehrId}`);
  return response.data;
}

export async function listProfiles(params: {
  department?: string;
  team_id?: number;
  skip?: number;
  limit?: number;
} = {}): Promise<PaginatedResponse<ProfileBase>> {
  const response = await api.get('/portrait/profiles', { params });
  return response.data;
}

export async function updateMyProfile(data: Partial<ProfileBase>): Promise<ProfileBase> {
  const response = await api.put('/portrait/profiles/me', data);
  return response.data;
}

export async function updateMyPolitical(data: Partial<PoliticalInfo>): Promise<PoliticalInfo> {
  const response = await api.put('/portrait/profiles/me/political', data);
  return response.data;
}

export async function updateMyEducation(data: Partial<EducationInfo>): Promise<EducationInfo> {
  const response = await api.put('/portrait/profiles/me/education', data);
  return response.data;
}

export async function updateMyFamily(data: Partial<FamilyInfo>): Promise<FamilyInfo> {
  const response = await api.put('/portrait/profiles/me/family', data);
  return response.data;
}

export async function updateMyContact(data: Partial<ContactInfo>): Promise<ContactInfo> {
  const response = await api.put('/portrait/profiles/me/contact', data);
  return response.data;
}

// ============================================================================
// Submission (4 端点)
// ============================================================================
export async function createSubmission(data: {
  submission_type: 'special_work' | 'profile_edit' | 'skill_tag_edit';
  payload: any;
  next_approver_id?: number;
}): Promise<SubmissionRecord> {
  const response = await api.post('/portrait/submissions', data);
  return response.data;
}

export async function listMySubmissions(params: {
  status?: string;
  submission_type?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<PaginatedResponse<SubmissionRecord>> {
  const response = await api.get('/portrait/submissions/me', { params });
  return response.data;
}

export async function getSubmissionDetail(submissionId: number): Promise<SubmissionDetail> {
  const response = await api.get(`/portrait/submissions/${submissionId}`);
  return response.data;
}

export async function cancelSubmission(submissionId: number): Promise<SubmissionRecord> {
  const response = await api.delete(`/portrait/submissions/${submissionId}`);
  return response.data;
}

// ============================================================================
// Approval (4 端点)
// ============================================================================
export async function listMyPendingApprovals(params: {
  skip?: number;
  limit?: number;
} = {}): Promise<PaginatedResponse<SubmissionRecord>> {
  const response = await api.get('/portrait/approvals/pending', { params });
  return response.data;
}

export async function listMyApprovalHistory(params: {
  skip?: number;
  limit?: number;
} = {}): Promise<PaginatedResponse<SubmissionRecord>> {
  const response = await api.get('/portrait/approvals/history', { params });
  return response.data;
}

export async function approveSubmission(
  submissionId: number,
  comment?: string
): Promise<ApprovalActionResponse> {
  const response = await api.post(`/portrait/approvals/${submissionId}/approve`, { comment });
  return response.data;
}

export async function rejectSubmission(
  submissionId: number,
  comment: string  // 必填, Rule 12 显性化
): Promise<ApprovalActionResponse> {
  const response = await api.post(`/portrait/approvals/${submissionId}/reject`, { comment });
  return response.data;
}

export async function transferSubmission(
  submissionId: number,
  transferredToId: number,
  comment?: string
): Promise<ApprovalActionResponse> {
  const response = await api.post(`/portrait/approvals/${submissionId}/transfer`, {
    transferred_to_id: transferredToId,
    comment,
  });
  return response.data;
}

// ============================================================================
// 审批人下拉数据 (复用后端 /users 端点)
// ============================================================================
export async function listUsersForApprover(params: {
  skip?: number;
  limit?: number;
} = {}): Promise<{ items: ApproverUser[]; total: number }> {
  // 注意: 用 /users/ 带尾斜杠避免 FastAPI 307 redirect 时丢失 Authorization header
  const response = await api.get('/users/', { params: { skip: params.skip ?? 0, limit: params.limit ?? 200 } });
  // 后端返回结构: { items: User[], total, page, size }, 这里收窄类型
  const data = response.data as { items?: any[]; total?: number };
  const items: ApproverUser[] = (data.items || []).map((u: any) => ({
    id: u.id,
    name: u.name,
    ehr_id: u.ehr_id,
  }));
  return { items, total: data.total ?? items.length };
}


// ============================================================================
// P6 家访审批 API
// ============================================================================
export interface HomeVisitItem {
  id: number;
  visited_ehr_id: string;
  visited_name: string;
  visit_year: number;
  visit_time: string;
  visit_method: string;
  is_visited: boolean;
  status: string;
  submitted_at: string | null;
  completed_at: string | null;
  visitor_name: string | null;
  current_approver_name: string | null;
  created_at: string;
}

export interface HomeVisitDetail extends HomeVisitItem {
  visited_user_id: number;
  visitor_user_id: number;
  visit_address: string | null;
  visitor_info: string | null;
  visit_date: string | null;
  position: string | null;
  contact_phone: string | null;
  address: string | null;
  mobile: string | null;
  home_phone: string | null;
  family1_name: string | null;
  family1_relation: string | null;
  family1_contact: string | null;
  family1_work_unit: string | null;
  family2_name: string | null;
  family2_relation: string | null;
  family2_contact: string | null;
  family2_work_unit: string | null;
  feedback: string | null;
  current_approver_id: number | null;
  updated_at: string;
}

export interface HomeVisitListResponse {
  total: number;
  items: HomeVisitItem[];
}

export interface HomeVisitCreatePayload {
  visited_ehr_id: string;
  visit_year: number;
  visit_time: string;
  visit_method: '线上' | '线下';
  visit_address?: string;
  visitor_info?: string;
  is_visited?: boolean;
  visit_date?: string;
  position?: string;
  contact_phone?: string;
  address?: string;
  mobile?: string;
  home_phone?: string;
  family1_name?: string;
  family1_relation?: string;
  family1_contact?: string;
  family1_work_unit?: string;
  family2_name?: string;
  family2_relation?: string;
  family2_contact?: string;
  family2_work_unit?: string;
  feedback?: string;
}

export async function listHomeVisits(params?: {
  status?: string;
  visit_year?: number;
  visited_ehr_id?: string;
  skip?: number;
  limit?: number;
}): Promise<HomeVisitListResponse> {
  const response = await api.get('/portrait/home-visits', { params });
  return response.data;
}

export async function getHomeVisit(id: number): Promise<HomeVisitDetail> {
  const response = await api.get(`/portrait/home-visits/${id}`);
  return response.data;
}

export async function createHomeVisit(
  payload: HomeVisitCreatePayload
): Promise<HomeVisitDetail> {
  const response = await api.post('/portrait/home-visits', payload);
  return response.data;
}

export async function updateHomeVisit(
  id: number,
  payload: Partial<HomeVisitCreatePayload>
): Promise<HomeVisitDetail> {
  const response = await api.put(`/portrait/home-visits/${id}`, payload);
  return response.data;
}

export async function submitHomeVisit(
  id: number,
  next_approver_id?: number
): Promise<HomeVisitDetail> {
  const response = await api.post(`/portrait/home-visits/${id}/submit`, {
    next_approver_id,
  });
  return response.data;
}

export async function cancelHomeVisit(id: number): Promise<HomeVisitDetail> {
  const response = await api.post(`/portrait/home-visits/${id}/cancel`);
  return response.data;
}

export async function approveHomeVisit(
  id: number,
  comment?: string
): Promise<HomeVisitDetail> {
  const response = await api.post(`/portrait/home-visits/${id}/approve`, { comment });
  return response.data;
}

export async function rejectHomeVisit(
  id: number,
  comment: string  // 必填, Rule 12
): Promise<HomeVisitDetail> {
  const response = await api.post(`/portrait/home-visits/${id}/reject`, { comment });
  return response.data;
}

// ============================================================================
// 培训记录 (PRD §10.3 占位, 批次 16)
// ============================================================================
export interface TrainingRecord {
  id: number;
  ehr_id: string;
  training_name: string;
  training_at: string;
  training_type: string;
  institution: string;
  certificate_no?: string | null;
  valid_until?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingImportSummary {
  success_count: number;
  failed_count: number;
  failed_rows: Array<{
    row_number: number;
    ehr_id: string;
    reason: string;
  }>;
}

/** D2 我的培训记录 */
export async function getMyTraining(): Promise<TrainingRecord[]> {
  const response = await api.get('/portrait/training/me');
  return response.data;
}

/** D2 跨人查看培训记录 */
export async function getTrainingByEhr(ehr: string): Promise<TrainingRecord[]> {
  const response = await api.get(`/portrait/training/by-ehr/${ehr}`);
  return response.data;
}

// ============================================================================
// 出入境台账 (PRD §10.1 F5-F9, 阶段 C)
// ============================================================================
export interface EntryExitRecord {
  id: number;
  ehr_id: string;
  name: string;
  team_name: string;
  position: string;
  certificate_no: string;
  outbound_reason: string;
  destination: string;
  apply_depart_at: string;
  apply_return_at: string;
  certificate_type: string;
  apply_type: string;
  team_approver: string;
  actual_depart_at?: string | null;
  actual_return_at?: string | null;
  year: number;
  group_name?: string | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntryExitStatistics {
  total_count: number;
  current_year_count: number;
  distinct_certificate_count: number;
  not_returned_count: number;
}

export interface EntryExitListResponse {
  items: EntryExitRecord[];
  total: number;
  page: number;
  size: number;
  statistics?: EntryExitStatistics;
}

export interface EntryExitCreate {
  ehr_id: string;
  name: string;
  team_name: string;
  position: string;
  certificate_no: string;
  outbound_reason: string;
  destination: string;
  apply_depart_at: string;
  apply_return_at: string;
  certificate_type: string;
  apply_type: string;
  team_approver: string;
  actual_depart_at?: string | null;
  actual_return_at?: string | null;
  year: number;
  group_name?: string | null;
  remark?: string | null;
}

/** F5 出入境台账列表 */
export async function getEntryExitRecords(params: {
  skip?: number;
  limit?: number;
  ehr_id?: string;
  name?: string;
  team_name?: string;
  year?: number;
  stats?: boolean;
}): Promise<EntryExitListResponse> {
  const response = await api.get('/portrait/entry-exit', { params });
  return response.data;
}

/** F6 新增出入境记录 */
export async function createEntryExit(data: EntryExitCreate): Promise<EntryExitRecord> {
  const response = await api.post('/portrait/entry-exit', data);
  return response.data;
}

/** F7 查看出入境记录 */
export async function getEntryExit(recordId: number): Promise<EntryExitRecord> {
  const response = await api.get(`/portrait/entry-exit/${recordId}`);
  return response.data;
}

/** F8 编辑出入境记录 */
export async function updateEntryExit(recordId: number, data: Partial<EntryExitCreate>): Promise<EntryExitRecord> {
  const response = await api.put(`/portrait/entry-exit/${recordId}`, data);
  return response.data;
}

/** F8 删除出入境记录 */
export async function deleteEntryExit(recordId: number): Promise<void> {
  const response = await api.delete(`/portrait/entry-exit/${recordId}`);
  return response.data;
}

/** F9 出入境批量导入 */
export async function importEntryExit(file: File): Promise<{ success_count: number; failed_count: number; failed_rows: Array<{ row_number: number; ehr_id: string; reason: string }> }> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/portrait/entry-exit/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

// ============================================================================
// 消防演练 (PRD §10.2 F2-F4, 阶段 D)
// ============================================================================
export interface DrillRecord {
  id: number;
  activity_date: string;
  drill_type: string;
  location: string;
  duration_minutes?: number | null;
  participant_count: number;
  created_at: string;
  updated_at: string;
}

export interface DrillParticipant {
  id: number;
  drill_id: number;
  ehr_id: string;
  name: string;
  participated: boolean;
}

export interface DrillDetail extends DrillRecord {
  participants: DrillParticipant[];
}

export interface DrillCreate {
  activity_date: string;
  drill_type: string;
  location: string;
  duration_minutes?: number | null;
  participant_ehr_ids: string[];
}

/** 矩阵单元格/行/整体 (F4) */
export interface MatrixCell { participated: boolean; value: string; }
export interface MatrixRow {
  user_id: number;
  ehr_id: string;
  name: string;
  team_name: string;
  position: string;
  cells: MatrixCell[];
  participated_count: number;
}
export interface DrillMatrix {
  columns: Array<{ drill_id: number; activity_date: string; drill_type: string; location: string }>;
  rows: MatrixRow[];
  total_drills: number;
  total_participants: number;
}

export interface DrillImportSummary {
  success_count: number;
  failed_count: number;
  failed_rows: Array<{ row_number: number; ehr_id: string; reason: string }>;
}

export interface DrillListResponse {
  items: DrillRecord[];
  total: number;
  page: number;
  size: number;
}

export async function getDrillRecords(params: {
  skip?: number;
  limit?: number;
  drill_type?: string;
  team_name?: string;
}): Promise<DrillListResponse> {
  const response = await api.get('/portrait/drills', { params });
  return response.data;
}

export async function getDrillMatrix(): Promise<DrillMatrix> {
  const response = await api.get('/portrait/drills/matrix');
  return response.data;
}

export async function createDrill(data: DrillCreate): Promise<DrillRecord> {
  const response = await api.post('/portrait/drills', data);
  return response.data;
}

export async function getDrillDetail(drillId: number): Promise<DrillDetail> {
  const response = await api.get(`/portrait/drills/${drillId}`);
  return response.data;
}

export async function deleteDrill(drillId: number): Promise<void> {
  const response = await api.delete(`/portrait/drills/${drillId}`);
  return response.data;
}

export async function importDrill(file: File): Promise<DrillImportSummary> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/portrait/drills/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}
