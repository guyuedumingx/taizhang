// 用户类型
export interface User {
  id: number;
  username: string | null;
  ehr_id: string | null;
  name: string | null;
  department: string | null;
  is_active: boolean | null;
  is_superuser: boolean;
  team_id: number | null;
  roles: string[] | null;
  password_expired?: boolean | null;
  last_password_change?: string | null;
}

export interface UserCreate {
  username: string;
  ehr_id: string;
  password: string;
  name: string | null;
  department: string | null;
  is_active?: boolean | null;
  is_superuser?: boolean;
  team_id?: number | null;
  role?: string | null;
}

export interface UserUpdate {
  username?: string | null;
  ehr_id?: string | null;
  password?: string | null;
  name?: string | null;
  department?: string | null;
  is_active?: boolean | null;
  is_superuser?: boolean;
  team_id?: number | null;
  role?: string | null;
}

// 团队类型
export interface Team {
  id: number;
  name: string | null;
  description: string | null;
  department?: string | null;
  leader_id: number | null;
  leader_name: string | null;
  member_count: number;
}

export interface TeamCreate {
  name: string;
  department: string;
  description?: string;
  leader_id: number | null;
}

export interface TeamUpdate {
  name?: string;
  department?: string;
  description?: string;
  leader_id?: number | null;
}

// 角色类型
export interface Role {
  id: number;
  name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
  created_at: string;
  updated_at: string | null;
}

export interface RoleCreate {
  name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  permissions?: string[];
  is_system?: boolean;
}

// 模板类型
/** 自动填充配置（与后端 auto_fill_config 一致） */
export interface AutoFillConfig {
  enabled?: boolean;
  api_url?: string;
  headers?: Record<string, string>;
  key_field_name?: string;
  field_mapping?: Record<string, string>;
}

export interface Template {
  id: number;
  name: string;
  description: string;
  department: string;
  created_by_id: number;
  updated_by_id: number;
  created_at: string | null;
  updated_at: string | null;
  default_description?: string;
  default_metadata?: object | null;
  auto_fill_config?: AutoFillConfig | null;
  created_by_name?: string;
  updated_by_name?: string;
  fields_count?: number;
  ledgers_count?: number;
  workflow_id: number | null;
  is_system: boolean;
}

export interface TemplateDetail extends Template {
  fields: Field[];
  auto_fill_trigger_fields?: string[];
}

export interface TemplateCreate {
  name: string;
  description?: string | null;
  department: string;
  is_system: boolean | null;
  default_description?: string | null;
  default_metadata?: object | null;
  auto_fill_config?: AutoFillConfig | null;
  fields: FieldCreate[];
  workflow_id?: number | null;
}

export interface TemplateUpdate {
  name?: string;
  department?: string;
  description?: string;
  is_system?: boolean | null;
  default_description?: string;
  default_metadata?: object | null;
  auto_fill_config?: AutoFillConfig | null;
  workflow_id?: number | null;
  fields?: FieldCreate[];
}

// 字段类型
export interface Field {
  id: number;
  template_id: number;
  name: string | null;
  label: string | null;
  type: string | null;
  required: boolean;
  order: number;
  options: string[] | null;
  default_value: string | null;
  is_key_field: boolean;
}

export interface FieldCreate {
  template_id?: number;
  name: string;
  label: string | null;
  type: string;
  required?: boolean;
  order?: number;
  options?: string[] | null;
  default_value?: string | null;
  is_key_field?: boolean;
}

export interface FieldUpdate {
  id?: number;
  name?: string;
  label?: string;
  type?: string;
  required?: boolean;
  order?: number;
  options?: string[] | null;
  default_value?: string | null;
  is_key_field?: boolean;
}

// 台账类型
export interface Ledger {
  id: number;
  name: string;
  description: string;
  status: string;
  approval_status: string;
  team_id: number | null;
  template_id: number | null;
  data: Record<string, unknown>;
  created_by_id: number;
  updated_by_id: number;
  current_approver_id: number | null;
  created_at: string;
  updated_at: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  team_name?: string;
  template_name?: string;
  created_by_name?: string;
  updated_by_name?: string;
  current_approver_name?: string;
  workflow_name?: string;
  active_workflow_instance?: WorkflowInstance;
}

export interface LedgerCreate {
  name: string;
  description?: string;
  template_id: number;
  team_id?: number | null;
  workflow_id?: number | null;
  data?: Record<string, unknown>;
  status?: string;
  approval_status?: string;
}

export interface LedgerUpdate {
  name?: string;
  description?: string;
  status?: string;
  team_id?: number | null;
  template_id?: number | null;
  data?: Record<string, unknown>;
  approval_status?: string;
}

export interface LedgerSubmit {
  workflow_id?: number;
  comment?: string;
  next_approver_id?: number;
}

export interface LedgerApproval {
  action: string;
  comment?: string;
  next_approver_id?: number;
}

export interface WorkflowNodeApproval {
  comment?: string;
  next_approver_id?: number;
}

export interface WorkflowNodeRejection {
  comment?: string;
}

// 工作流类型
export interface WorkflowNode {
  id: number;
  workflow_id: number;
  name: string;
  description: string;
  node_type: string;
  approver_role_id: number | null;
  order_index: number;
  is_final: boolean;
  reject_to_node_id: number | null;
  multi_approve_type: string;
  created_at: string;
  updated_at: string | null;
  approvers?: Array<{id: number; name: string}>;
  approver_role_name?: string;
  approver_user_name?: string;
}

export interface WorkflowNodeCreate {
  workflow_id: number;
  name: string;
  description: string;
  node_type: string;
  approver_role_id?: number | null;
  order_index: number;
  is_final?: boolean;
  reject_to_node_id?: number | null;
  multi_approve_type?: string;
  approver_ids?: number[];
}

export interface WorkflowNodeUpdate {
  name?: string;
  description?: string;
  node_type?: string;
  approver_role_id?: number | null;
  order_index?: number;
  is_final?: boolean;
  reject_to_node_id?: number | null;
  multi_approve_type?: string;
  approver_ids?: number[];
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  template_id: number;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string | null;
  nodes: WorkflowNode[];
  template_name?: string;
  creator_name?: string;
  node_count?: number;
}

export interface WorkflowCreate {
  name: string;
  description: string;
  is_active?: boolean;
  nodes: WorkflowNodeCreate[];
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  nodes?: WorkflowNodeCreate[];
}

export interface WorkflowInstanceNode {
  id: number;
  workflow_instance_id: number;
  workflow_node_id: number;
  status: string;
  approver_id: number | null;
  comment: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  approver_name?: string;
  node_name?: string;
  node_type?: string;
  approver_actions?: Array<{
    user_id: number;
    user_name?: string;
    action: string;
    comment?: string;
    timestamp?: string;
  }>;
}

export interface WorkflowInstance {
  id: number;
  workflow_id: number;
  ledger_id: number;
  status: string;
  current_node_id: number | null;
  created_by: number;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  nodes: WorkflowInstanceNode[];
  workflow_name?: string;
  ledger_name?: string;
  creator_name?: string;
  current_node_name?: string;
  current_node?: WorkflowInstanceNode;
}

// 日志类型
export interface SystemLog {
  id: number;
  user_id: number | null;
  ip_address: string | null;
  user_agent: string | null;
  level: string;
  module: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  ledger_id: number | null;
  workflow_instance_id: number | null;
  action: string;
  status_before: string | null;
  status_after: string | null;
  comment: string | null;
  created_at: string;
}

export interface LogQueryParams {
  module?: string;
  action?: string;
  level?: string;
  user_id?: number;
  resource_type?: string;
  resource_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
  date_range?: [string, string] | null;
  keyword?: string;
  ledger_id?: number;
  ip_address?: string;
}

// 认证类型
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  name: string;
  roles: string[];
  permissions: string[];
  team_id: number | null;
  password_expired: boolean;
}

export interface RegisterRequest {
  username: string;
  password: string;
  ehr_id: string;
  name: string;
  department: string;
}

// 分页相关类型
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// API响应类型
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
} 

export interface OverviewResponse {
  users_count: number;
  teams_count: number;
  templates: Template[];
  ledgers: Ledger[];
}

// 自动填充触发配置
export interface AutoFillTriggerConfig {
  id: number;
  field_name: string;
  api_url: string;
  headers?: Record<string, string> | null;
  timeout?: number;
  retry_times?: number;
  enabled: boolean;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AutoFillTriggerConfigCreate {
  field_name: string;
  api_url: string;
  headers?: Record<string, string> | null;
  timeout?: number;
  retry_times?: number;
  enabled?: boolean;
  description?: string | null;
}

export interface AutoFillTriggerConfigUpdate {
  field_name?: string;
  api_url?: string;
  headers?: Record<string, string> | null;
  timeout?: number;
  retry_times?: number;
  enabled?: boolean;
  description?: string | null;
}
// ===== 数字画像（portrait） =====

export interface PortraitProfileBase {
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
  is_emergency_staff?: boolean | null;
}

export interface PortraitPoliticalInfo {
  id: number;
  profile_id: number;
  political_status?: string | null;
  join_date?: string | null;
  introducer?: string | null;
}

export interface PortraitEducationInfo {
  id: number;
  profile_id: number;
  education_category?: string | null;
  education_type?: string | null;
  education_level?: string | null;
  degree?: string | null;
  school?: string | null;
  major_name?: string | null;
  duration_years?: string | null;
  enrollment_date?: string | null;
  graduation_date?: string | null;
  completion_status?: string | null;
  country?: string | null;
}

export interface PortraitFamilyInfo {
  id: number;
  profile_id: number;
  name?: string | null;
  gender?: string | null;
  relation?: string | null;
  birth_date?: string | null;
  work_unit_and_title?: string | null;
  political_status?: string | null;
  employment_status?: string | null;
}

export interface PortraitResumeInfo {
  id: number;
  profile_id: number;
  start_time?: string | null;
  end_time?: string | null;
  unit_and_title?: string | null;
}

export interface PortraitRewardInfo {
  id: number;
  profile_id: number;
  reward_type?: string | null;
  reward_time?: string | null;
  reward_name?: string | null;
  reward_reason?: string | null;
}

export interface PortraitQualificationInfo {
  id: number;
  profile_id: number;
  qualification_name?: string | null;
  obtain_time?: string | null;
  valid_until?: string | null;
}

export interface PortraitAchievementInfo {
  id: number;
  profile_id: number;
  achievement_name?: string | null;
  obtain_time?: string | null;
}

export interface PortraitLanguageInfo {
  id: number;
  profile_id: number;
  language?: string | null;
  proficiency?: string | null;
  cert_level_or_score?: string | null;
}

export interface PortraitContactInfo {
  id: number;
  profile_id: number;
  mobile?: string | null;
  office_phone?: string | null;
  home_phone?: string | null;
  home_address?: string | null;
  email?: string | null;
  commute_minutes?: number | null;
}

export interface PortraitSkillTag {
  id: number;
  profile_id: number;
  tag_name: string;
  template_id?: number | null;
}

export interface PortraitDevelopmentIntent {
  id: number;
  profile_id: number;
  development_path?: string | null;
  short_term_goal?: string | null;
  mid_term_goal?: string | null;
  core_abilities: string[];
  learning_methods: string[];
  learning_courses?: string | null;
  rotation_interest?: string | null;
  rotation_target?: string | null;
  project_interests: string[];
  other_comments?: string | null;
}

export interface PortraitProjectSummary {
  id: number;
  profile_id: number;
  project_name: string;
  start_time?: string | null;
  end_time?: string | null;
  role?: string | null;
  description?: string | null;
  tag_ids: number[];
  tag_names: string[];
}

export interface PortraitProfileFull {
  user_id: number;
  ehr_no: string;
  name: string;
  group_name?: string | null;
  base?: PortraitProfileBase | null;
  political: PortraitPoliticalInfo[];
  education: PortraitEducationInfo[];
  family: PortraitFamilyInfo[];
  resume: PortraitResumeInfo[];
  reward: PortraitRewardInfo[];
  qualification: PortraitQualificationInfo[];
  achievement: PortraitAchievementInfo[];
  language: PortraitLanguageInfo[];
  contact?: PortraitContactInfo | null;
  skill_tags: PortraitSkillTag[];
  development_intent?: PortraitDevelopmentIntent | null;
  project_summaries: PortraitProjectSummary[];
}
