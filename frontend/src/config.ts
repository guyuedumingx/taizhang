// API基础URL
export const API_BASE_URL = process.env.NODE_ENV === 'test' 
  ? 'http://localhost:8080/api/v1'
  : '/api/v1';

// 分页默认参数
export const DEFAULT_PAGE_SIZE = 10;
export const DEFAULT_PAGE = 1;

// 系统权限
export const PERMISSIONS = {
  // 台账权限
  LEDGER_VIEW: 'ledger:view',
  LEDGER_CREATE: 'ledger:create',
  LEDGER_EDIT: 'ledger:edit',
  LEDGER_DELETE: 'ledger:delete',
  LEDGER_EXPORT: 'ledger:export',
  LEDGER_SUBMIT: 'ledger:submit',
  LEDGER_APPROVE: 'ledger:approve',
  LEDGER_ADMIN_APPROVE: 'ledger:admin_approve',
  
  // 模板权限
  TEMPLATE_VIEW: 'template:view',
  TEMPLATE_CREATE: 'template:create',
  TEMPLATE_EDIT: 'template:edit',
  TEMPLATE_DELETE: 'template:delete',
  
  // 字段权限
  FIELD_VIEW: 'field:view',
  FIELD_CREATE: 'field:create',
  FIELD_EDIT: 'field:edit',
  FIELD_DELETE: 'field:delete',
  
  // 工作流权限
  WORKFLOW_VIEW: 'workflow:view',
  WORKFLOW_CREATE: 'workflow:create',
  WORKFLOW_EDIT: 'workflow:edit',
  WORKFLOW_DELETE: 'workflow:delete',
  
  // 审批权限
  APPROVAL_VIEW: 'approval:view',
  APPROVAL_SUBMIT: 'approval:submit',
  APPROVAL_APPROVE: 'approval:approve',
  APPROVAL_REJECT: 'approval:reject',
  
  // 用户权限
  USER_VIEW: 'user:view',
  USER_CREATE: 'user:create',
  USER_EDIT: 'user:edit',
  USER_DELETE: 'user:delete',
  
  // 角色权限
  ROLE_VIEW: 'role:view',
  ROLE_CREATE: 'role:create',
  ROLE_EDIT: 'role:edit',
  ROLE_DELETE: 'role:delete',
  
  // 团队权限
  TEAM_VIEW: 'team:view',
  TEAM_CREATE: 'team:create',
  TEAM_EDIT: 'team:edit',
  TEAM_DELETE: 'team:delete',
  
  // 权限管理
  PERMISSION_VIEW: 'permission:view',
  PERMISSION_ASSIGN: 'permission:assign',
  
  // 日志权限
  LOG_VIEW: 'log:view',
};

// 登录页面背景图
export const LOGIN_BG_IMAGE = '/assets/images/login-bg.jpg';

// 系统名称
export const SYSTEM_NAME = '台账管理系统';

// 系统Logo
export const SYSTEM_LOGO = '/assets/images/logo.png';

// 系统版本
export const SYSTEM_VERSION = 'v1.0.0';

// 系统页脚
export const SYSTEM_FOOTER = `${SYSTEM_NAME} ©${new Date().getFullYear()} 版权所有`;

// 密码规则
export const PASSWORD_RULES = {
  MIN_LENGTH: 8,
  REQUIRE_NUMBER: true,
  REQUIRE_LOWERCASE: true,
  REQUIRE_UPPERCASE: true,
  REQUIRE_SPECIAL: true,
};

// 密码到期时间（天）
export const PASSWORD_EXPIRES_DAYS = 90;

// 分页默认配置
export const PAGE_SIZE_OPTIONS = ['10', '20', '50', '100']; 