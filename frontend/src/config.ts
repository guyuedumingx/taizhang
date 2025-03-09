// API基础URL
// export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'; 

// 分页默认配置
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = ['10', '20', '50', '100'];

// 权限常量
export const PERMISSIONS = {
  // 台账权限
  LEDGER_VIEW: 'ledger:view',
  LEDGER_CREATE: 'ledger:create',
  LEDGER_EDIT: 'ledger:edit',
  LEDGER_DELETE: 'ledger:delete',
  LEDGER_EXPORT: 'ledger:export',
  LEDGER_APPROVE: 'ledger:approve',
  LEDGER_ADMIN_APPROVE: 'ledger:admin_approve',
  
  // 模板权限
  TEMPLATE_VIEW: 'template:view',
  TEMPLATE_CREATE: 'template:create',
  TEMPLATE_EDIT: 'template:edit',
  TEMPLATE_DELETE: 'template:delete',
  
  // 用户管理权限
  USER_VIEW: 'user:view',
  USER_CREATE: 'user:create',
  USER_EDIT: 'user:edit',
  USER_DELETE: 'user:delete',
  
  // 角色管理权限
  ROLE_VIEW: 'role:view',
  ROLE_CREATE: 'role:create',
  ROLE_EDIT: 'role:edit',
  ROLE_DELETE: 'role:delete',
  
  // 团队管理权限
  TEAM_VIEW: 'team:view',
  TEAM_CREATE: 'team:create',
  TEAM_EDIT: 'team:edit',
  TEAM_DELETE: 'team:delete',
  
  // 工作流管理权限
  WORKFLOW_VIEW: 'workflow:view',
  WORKFLOW_CREATE: 'workflow:create',
  WORKFLOW_EDIT: 'workflow:edit',
  WORKFLOW_DELETE: 'workflow:delete',
  
  // 日志查看权限
  LOG_VIEW: 'log:view',
}; 