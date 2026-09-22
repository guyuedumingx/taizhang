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
