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
  created_at?: string;
  updated_at?: string | null;
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
  permissions: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  permissions?: string[];
}

// 模板类型
export interface Template {
  id: number;
  name: string;
  description: string;
  department: string;
  is_system: boolean;
  created_by_id: number;
  updated_by_id?: number;
  created_at: string;
  updated_at: string | null;
  created_by_name?: string;
  updated_by_name?: string;
  fields_count?: number;
  ledgers_count?: number;
  
  // 台账元字段（默认值）
  default_ledger_name?: string;
  default_description?: string;
  default_status?: string;
  default_team_id?: number;
  default_team_name?: string;
  default_metadata?: Record<string, unknown>;
}

export interface TemplateDetail extends Template {
  fields: Field[];
}

export interface TemplateCreate {
  name: string;
  description: string;
  department: string;
  default_ledger_name?: string;
  default_description?: string;
  default_status?: string;
  default_team_id?: number;
  default_metadata?: Record<string, unknown>;
  fields?: FieldCreate[];
}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  department?: string;
  default_ledger_name?: string;
  default_description?: string;
  default_status?: string;
  default_team_id?: number;
  default_metadata?: Record<string, unknown>;
  fields?: FieldCreate[];
}

// 字段类型
export interface Field {
  id: number;
  template_id: number;
  name: string;
  label: string;
  type: string;
  required: boolean;
  order: number;
  options: string[] | null;
  default_value: string | null;
  is_key_field: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface FieldCreate {
  template_id?: number;
  name: string;
  label: string;
  type: string;
  required?: boolean;
  order?: number;
  options?: string[] | null;
  default_value?: string | null;
  is_key_field?: boolean;
}

export interface FieldUpdate {
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
  workflow_id: number | null;
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
}

export interface LedgerUpdate {
  name?: string;
  description?: string;
  status?: string;
  team_id?: number | null;
  template_id?: number | null;
  workflow_id?: number | null;
  data?: Record<string, unknown>;
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

// 工作流类型
export interface WorkflowNode {
  id: number;
  workflow_id: number;
  name: string;
  description: string;
  node_type: string;
  approver_role_id: number | null;
  approver_user_id: number | null;
  order_index: number;
  is_final: boolean;
  reject_to_node_id: number | null;
  multi_approve_type: string;
  need_select_next_approver: boolean;
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
  approver_user_id?: number | null;
  order_index: number;
  is_final?: boolean;
  reject_to_node_id?: number | null;
  multi_approve_type?: string;
  need_select_next_approver?: boolean;
  approver_ids?: number[];
}

export interface WorkflowNodeUpdate {
  name?: string;
  description?: string;
  node_type?: string;
  approver_role_id?: number | null;
  approver_user_id?: number | null;
  order_index?: number;
  is_final?: boolean;
  reject_to_node_id?: number | null;
  multi_approve_type?: string;
  need_select_next_approver?: boolean;
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
}

export interface WorkflowCreate {
  name: string;
  description: string;
  template_id: number;
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