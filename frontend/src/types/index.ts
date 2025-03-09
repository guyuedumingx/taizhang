// 用户相关类型
export interface User {
  id: number;
  username: string;
  ehr_id: string;
  name: string;
  department?: string;
  is_active: boolean;
  is_superuser: boolean;
  team_id?: number;
  roles?: string[];
}

export interface UserCreate {
  username: string;
  ehr_id: string;
  password: string;
  name: string;
  department?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  team_id?: number;
  roles?: string[];
}

export interface UserUpdate {
  username?: string;
  ehr_id?: string;
  password?: string;
  name?: string;
  department?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  team_id?: number;
  roles?: string[];
}

// 团队相关类型
export interface Team {
  id: number;
  name: string;
  department: string;
  description?: string;
  leader_id?: number;
  leader_name?: string;
  member_count: number;
}

export interface TeamCreate {
  name: string;
  department: string;
  description?: string;
  leader_id?: number;
}

export interface TeamUpdate {
  name?: string;
  department?: string;
  description?: string;
  leader_id?: number;
}

// 角色相关类型
export interface Role {
  id: number;
  name: string;
  description?: string;
  is_system: boolean;
  created_at: string;
  updated_at?: string;
  permissions: string[];
}

export interface RoleCreate {
  name: string;
  description?: string;
  permissions?: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  permissions?: string[];
}

// 模板相关类型
export interface Template {
  id: number;
  name: string;
  description?: string;
  department: string;
  is_system: boolean;
  created_by_id: number;
  created_by_name?: string;
  updated_by_id?: number;
  updated_by_name?: string;
  created_at: string;
  updated_at?: string;
  field_count: number;
}

export interface TemplateDetail extends Template {
  fields: Field[];
}

export interface TemplateCreate {
  name: string;
  description?: string;
  department: string;
  fields?: FieldCreate[];
}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  department?: string;
  fields?: FieldCreate[];
}

// 字段相关类型
export interface Field {
  id: number;
  name: string;
  label?: string;
  type: string;
  required: boolean;
  options?: string[];
  default_value?: string;
  order: number;
  template_id: number;
  is_key_field?: boolean;
}

export interface FieldCreate {
  name: string;
  label?: string;
  type: string;
  required?: boolean;
  options?: string[];
  default_value?: string;
  order?: number;
  is_key_field?: boolean;
}

export interface FieldUpdate {
  name?: string;
  label?: string;
  type?: string;
  required?: boolean;
  options?: string[];
  default_value?: string;
  order?: number;
  is_key_field?: boolean;
}

// 台账相关类型
export interface Ledger {
  id: number;
  name: string;
  description?: string;
  status: string;
  team_id?: number;
  team_name?: string;
  template_id?: number;
  template_name?: string;
  data?: Record<string, unknown>;
  created_by_id: number;
  created_by_name?: string;
  updated_by_id: number;
  updated_by_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface LedgerCreate {
  name: string;
  description?: string;
  status?: string;
  team_id?: number;
  template_id?: number;
  data?: Record<string, unknown>;
}

export interface LedgerUpdate {
  name?: string;
  description?: string;
  status?: string;
  team_id?: number;
  template_id?: number;
  data?: Record<string, unknown>;
}

// 认证相关类型
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    username: string;
    name: string;
    role: string;
    permissions: string[];
    teamId?: number;
  };
}

export interface RegisterRequest {
  username: string;
  password: string;
  ehr_id: string;
  name: string;
} 