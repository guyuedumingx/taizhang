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
  // P0.1 隐私裁剪: 移除 id_number / native_place / birth_place / household_place
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
  // P0.1 隐私裁剪: 移除 mobile / address / emergency_contact / emergency_phone
  email?: string | null;
  commute_minutes?: number | null;
}

// P0.2 新增: A4 兴趣 (PRD §5.4)
export interface InterestInfo {
  id?: number;
  profile_id?: number;
  interest_name: string;
  proficiency: '入门' | '熟练' | '精通';
}

// P0.2 新增: A5 获奖 (PRD §5.5)
export interface AwardInfo {
  id?: number;
  profile_id?: number;
  award_name: string;
  awarding_organization?: string | null;
  award_time?: string | null;
  level?: '国家级' | '省部级' | '行级' | null;
}

// P0.7 新增: B2 活动申报落子表 (PRD §6.2 v2.1, 审批通过后落入)
export interface ActivityRecord {
  id?: number;
  profile_id?: number;
  activity_name: string;
  activity_time: string;  // YYYY-MM-DD
  activity_type: '运动会' | '文艺' | '志愿' | '培训' | '其他';
  organizer: string;
  award_or_participation?: string | null;
  content?: string | null;
  hours?: number | null;
  source_submission_id?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface ProfileFull extends ProfileBase {
  user_name?: string | null;
  ehr_id?: string | null;
  department?: string | null;
  political?: PoliticalInfo | null;
  education?: EducationInfo | null;
  family?: FamilyInfo | null;
  contact?: ContactInfo | null;
  // P0.2 新增
  interests?: InterestInfo[] | null;
  awards?: AwardInfo[] | null;
  // P0.7 新增
  activities?: ActivityRecord[] | null;
  // Week 2 P0.5: A1 12 卡片 - 5 张 1:N 子表 + 技能标签
  resume?: ResumeInfo[] | null;
  reward?: RewardInfo[] | null;
  qualification?: QualificationInfo[] | null;
  achievement?: AchievementInfo[] | null;
  language?: LanguageInfo[] | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface SubmissionRecord {
  id: number;
  submission_type: 'special_work' | 'profile_edit' | 'activity_claim';
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

// P0.2: A4 兴趣爱好
export async function updateMyInterest(data: Partial<InterestInfo>): Promise<InterestInfo> {
  const response = await api.put('/portrait/profiles/me/interest', data);
  return response.data;
}

// P0.2: A5 获奖信息
export async function updateMyAward(data: Partial<AwardInfo>): Promise<AwardInfo> {
  const response = await api.put('/portrait/profiles/me/award', data);
  return response.data;
}

// ============================================================================
// Submission (4 端点)
// ============================================================================
export async function createSubmission(data: {
  submission_type: 'special_work' | 'profile_edit' | 'activity_claim';
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
  // C1 (PRD §7.1)
  co_visitor_name: string | null;
  team_name: string | null;
  has_scan: boolean;
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
  // C1 (PRD §7.1) 新增字段
  co_visitor_user_id: number | null;
  scan_file_path: string | null;
  scan_file_url: string | null;
  // PRD 附录 B.4 第 14 列「家访记录表扫描件」: 已提交 / 未提交
  scan_status: string | null;
}

// ============================================================================
// F11 批量导入 / F12 年度矩阵 / 批量导出 Excel
// ============================================================================
export interface HomeVisitImportRowFailure {
  row_number: number;
  ehr_id: string;
  reason: string;
}

export interface HomeVisitImportSummary {
  success_count: number;
  failed_count: number;
  failed_rows: HomeVisitImportRowFailure[];
}

/** F12 单元格: 填该年具体家访日期 (§7.2 的"绿色"由前端按 value 是否为空决定) */
export interface HomeVisitMatrixCell {
  visit_date: string | null;
  count: number;
  value: string;
}

export interface HomeVisitMatrixRow {
  seq: number;
  user_id: number;
  ehr_id: string;
  name: string;
  team_name: string;
  cells: HomeVisitMatrixCell[];
  /** 家访年度汇总 (B.2 第 8 列), 例 "2023年/2026年" */
  visited_years: string;
}

export interface HomeVisitMatrix {
  columns: Array<{ year: number }>;
  rows: HomeVisitMatrixRow[];
  total_years: number;
  total_visited_users: number;
}

export interface HomeVisitImportFileResponse {
  blob: Blob;
  filename: string;
}

/**
 * 下载 blob 文件并触发浏览器保存。
 * 单独抽出来是因为家访明细表的中文文件名走 RFC 5987 (filename*=UTF-8''...),
 * 不能靠 <a download="中文名"> —— 各浏览器行为不一致, 且 axios 拿不到真实文件名。
 */
export async function downloadBlob(
  url: string,
  params: Record<string, unknown>,
  fallbackName: string,
  mime: string,
): Promise<HomeVisitImportFileResponse> {
  const response = await api.get(url, { params, responseType: 'blob' });
  // 从 Content-Disposition 里取后端给的文件名 (取不到就用 fallback)
  let filename = fallbackName;
  const cd = response.headers?.['content-disposition'];
  if (cd) {
    const star = /filename\*=UTF-8''([^;]+)/i.exec(cd);
    const plain = /filename="?([^";]+)"?/i.exec(cd);
    if (star) {
      try {
        filename = decodeURIComponent(star[1]);
      } catch {
        /* 文件名没转义好就用 fallback, 不能因下载失败整个报错 */
      }
    } else if (plain) {
      filename = plain[1];
    }
  }
  const blob = new Blob([response.data], { type: mime });
  const objectUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(objectUrl);
  return { blob, filename };
}

const XLSX_MIME =
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

export function downloadHomeVisitTemplate(): Promise<HomeVisitImportFileResponse> {
  return downloadBlob(
    '/portrait/templates/excel/home-visit',
    {},
    '家访明细_导入模板.xlsx',
    XLSX_MIME
  );
}

export function exportHomeVisitsExcel(params?: {
  status?: string;
  visit_year?: number;
  visited_ehr_id?: string;
}): Promise<HomeVisitImportFileResponse> {
  return downloadBlob(
    '/portrait/home-visits/export',
    params || {},
    '家访明细表.xlsx',
    XLSX_MIME
  );
}

export async function importHomeVisits(file: File): Promise<HomeVisitImportSummary> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/portrait/home-visits/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getHomeVisitMatrix(params?: {
  team_name?: string;
  include_pending?: boolean;
}): Promise<HomeVisitMatrix> {
  const response = await api.get('/portrait/home-visits/matrix', { params });
  return response.data;
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
  // C1 (PRD §7.1) 新增字段
  co_visitor_user_id?: number | null;
  scan_file_path?: string | null;
  team_name?: string | null;
  // PRD 附录 B.4 第 14 列「家访记录表扫描件」: 已提交 / 未提交
  scan_status?: '已提交' | '未提交' | null;
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
// A1 12 卡片 (PRD §5.1) - 5 张 1:N 子表 + 技能标签 (Week 2 P0.5)
// ============================================================================
export interface ResumeInfo {
  id?: number;
  profile_id?: number;
  start_time?: string | null;
  end_time?: string | null;
  unit_and_title?: string | null;
}
export interface RewardInfo {
  id?: number;
  profile_id?: number;
  reward_type?: string | null;
  reward_time?: string | null;
  reward_name?: string | null;
  reward_reason?: string | null;
}
export interface QualificationInfo {
  id?: number;
  profile_id?: number;
  qualification_name?: string | null;
  obtain_time?: string | null;
  valid_until?: string | null;
}
export interface AchievementInfo {
  id?: number;
  profile_id?: number;
  achievement_name?: string | null;
  obtain_time?: string | null;
}
export interface LanguageInfo {
  id?: number;
  profile_id?: number;
  language?: string | null;
  proficiency?: string | null;
  cert_level_or_score?: string | null;
}
// 简历
export const addResume = (data: Partial<ResumeInfo>) =>
  api.post<ResumeInfo>('/portrait/profiles/me/resume', data).then((r) => r.data);
export const updateResume = (id: number, data: Partial<ResumeInfo>) =>
  api.put<ResumeInfo>(`/portrait/profiles/me/resume/${id}`, data).then((r) => r.data);
export const deleteResume = (id: number) =>
  api.delete(`/portrait/profiles/me/resume/${id}`).then((r) => r.data);

// 奖惩
export const addReward = (data: Partial<RewardInfo>) =>
  api.post<RewardInfo>('/portrait/profiles/me/reward', data).then((r) => r.data);
export const updateReward = (id: number, data: Partial<RewardInfo>) =>
  api.put<RewardInfo>(`/portrait/profiles/me/reward/${id}`, data).then((r) => r.data);
export const deleteReward = (id: number) =>
  api.delete(`/portrait/profiles/me/reward/${id}`).then((r) => r.data);

// 资格
export const addQualification = (data: Partial<QualificationInfo>) =>
  api.post<QualificationInfo>('/portrait/profiles/me/qualification', data).then((r) => r.data);
export const updateQualification = (id: number, data: Partial<QualificationInfo>) =>
  api.put<QualificationInfo>(`/portrait/profiles/me/qualification/${id}`, data).then((r) => r.data);
export const deleteQualification = (id: number) =>
  api.delete(`/portrait/profiles/me/qualification/${id}`).then((r) => r.data);

// 成果
export const addAchievement = (data: Partial<AchievementInfo>) =>
  api.post<AchievementInfo>('/portrait/profiles/me/achievement', data).then((r) => r.data);
export const updateAchievement = (id: number, data: Partial<AchievementInfo>) =>
  api.put<AchievementInfo>(`/portrait/profiles/me/achievement/${id}`, data).then((r) => r.data);
export const deleteAchievement = (id: number) =>
  api.delete(`/portrait/profiles/me/achievement/${id}`).then((r) => r.data);

// 语言
export const addLanguage = (data: Partial<LanguageInfo>) =>
  api.post<LanguageInfo>('/portrait/profiles/me/language', data).then((r) => r.data);
export const updateLanguage = (id: number, data: Partial<LanguageInfo>) =>
  api.put<LanguageInfo>(`/portrait/profiles/me/language/${id}`, data).then((r) => r.data);
export const deleteLanguage = (id: number) =>
  api.delete(`/portrait/profiles/me/language/${id}`).then((r) => r.data);

// ============================================================================
// A11 应急先锋队标识 (Week 3 P0.4) — 仅 admin 直改
// ============================================================================
export const setEmergencyStaff = (
  targetUserId: number,
  data: { is_emergency_staff: boolean; reason?: string }
) =>
  api
    .put<ProfileFull>(`/portrait/profiles/admin/users/${targetUserId}/emergency-staff`, data)
    .then((r) => r.data);

// ============================================================================
// C1 (PRD §7.1) — 扫描件上传/删除
// ============================================================================
export interface UploadScanResponse {
  file_path: string;       // 相对路径 (e.g. "home_visits/2026/abc123.pdf")
  file_url: string;        // 静态 URL (e.g. "/uploads/portrait/home_visits/2026/abc123.pdf")
  file_size: number;       // 字节
  original_name: string;   // 原始文件名
}

/**
 * 上传家访扫描件 (PDF/JPG/PNG, ≤5MB, 仅 leader/admin)
 * 返回的 file_path 应传给 createHomeVisit 的 scan_file_path 字段
 */
export async function uploadHomeVisitScanFile(file: File): Promise<UploadScanResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/portrait/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * 删除已上传的扫描件 (按 file_path)
 * 防路径遍历: 后端拒绝 ".." 和绝对路径
 */
export async function deleteHomeVisitScanFile(filePath: string): Promise<void> {
  await api.delete(`/portrait/files/${filePath}`);
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

export interface DrillMatrixParams {
  /** 按演练年份筛选列 */
  year?: number | null;
  /** 按团队筛选行 */
  team_name?: string | null;
}

export async function getDrillMatrix(params: DrillMatrixParams = {}): Promise<DrillMatrix> {
  const response = await api.get('/portrait/drills/matrix', { params });
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

// ============================================================
// G7 组员调换历史 (Week 3 P0.5, PRD §11.4)
// 只读 + 可删除 —— 没有新增/编辑接口, 记录由调组自动产生
// ============================================================
export interface GroupTransferRecord {
  id: number;
  user_id: number;
  user_name: string | null;
  ehr_no: string;
  from_group: string | null;
  to_group: string;
  from_team_id: number | null;
  to_team_id: number | null;
  transfer_date: string;
  leave_date: string | null;
  /** leave_date is None → 该员工目前仍在这一组 */
  is_current: boolean;
  operator_ehr_no: string;
  operator_name: string;
  reason: string | null;
  remark: string | null;
  created_at: string;
}

export interface GroupTransferListResponse {
  items: GroupTransferRecord[];
  total: number;
  page: number;
  size: number;
}

/** G7 调换历史列表: admin 全员 / 组长本组相关 */
export async function getGroupTransferRecords(params: {
  skip?: number;
  limit?: number;
  ehr_id?: string;
  name?: string;
  year?: number;
  is_current?: boolean;
}): Promise<GroupTransferListResponse> {
  const response = await api.get('/portrait/group-transfers', { params });
  return response.data;
}

/** G7 删除一条**已关闭**的记录 (仅 admin 纠错; 开区间记录后端会拒绝) */
export async function deleteGroupTransferRecord(recordId: number): Promise<void> {
  const response = await api.delete(`/portrait/group-transfers/${recordId}`);
  return response.data;
}
