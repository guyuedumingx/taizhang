// 用户类型
export interface User {
  id: number;
  username: string;
  ehr_id: string;
  name: string;
  department: string;
  is_active: boolean;
  is_superuser: boolean;
  team_id: number | null;
  team_name?: string;
  roles: string[];
}

export interface UserCreate {
  username: string;
  ehr_id: string;
  password: string;
  name: string;
  department: string;
  is_active?: boolean;
  is_superuser?: boolean;
  team_id?: number | null;
}

export interface UserUpdate {
  username?: string;
  ehr_id?: string;
  password?: string;
  name?: string;
  department?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  team_id?: number | null;
}

// 团队类型
export interface Team {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}

export interface TeamCreate {
  name: string;
  description: string;
}

export interface TeamUpdate {
  name?: string;
  description?: string;
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
  type: string;
  require_approval: boolean;
  default_workflow_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface TemplateDetail extends Template {
  fields: Field[];
}

export interface TemplateCreate {
  name: string;
  description: string;
  department: string;
  type?: string;
  require_approval?: boolean;
  default_workflow_id?: number | null;
}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  department?: string;
  type?: string;
  require_approval?: boolean;
  default_workflow_id?: number | null;
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
  template_id: number;
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
  team_id?: number | null;
  template_id?: number | null;
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
}

export interface LedgerApproval {
  action: string;
  comment?: string;
  next_approver_id?: number;
  approved?: boolean;
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
  created_at: string;
  updated_at: string | null;
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
}

export interface WorkflowNodeUpdate {
  name?: string;
  description?: string;
  approver_role_id?: number | null;
  approver_user_id?: number | null;
  order_index?: number;
  is_final?: boolean;
  reject_to_node_id?: number | null;
}

export interface Workflow {
  id: number;
  name: string;
  description: string;
  template_id: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  nodes: WorkflowNode[];
  template_name?: string;
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
  teamId: number | null;
  password_expired: boolean;
}

export interface RegisterRequest {
  username: string;
  ehr_id: string;
  password: string;
  name: string;
  department: string;
} 