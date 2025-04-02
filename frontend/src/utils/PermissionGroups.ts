import { PERMISSIONS } from '../config';

// 定义权限接口
export interface Permission {
  key: string;
  name: string;
  description: string;
  group: string;
}

// 定义权限组接口
export interface PermissionGroup {
  name: string;
  permissions: Permission[];
}

// 另一种格式的权限组（用于RoleManagement组件）
export interface PermissionGroupSimple {
  groupName: string;
  permissions: Array<{ key: string; label: string }>;
}

// 获取详细权限组列表（用于PermissionManagement组件）
export const getPermissionGroups = (): PermissionGroup[] => {
  return [
    {
      name: '台账管理',
      permissions: [
        { key: PERMISSIONS.LEDGER_VIEW, name: '查看台账', description: '允许查看台账列表和详情', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_CREATE, name: '创建台账', description: '允许创建新的台账', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_EDIT, name: '编辑台账', description: '允许编辑现有台账', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_DELETE, name: '删除台账', description: '允许删除台账', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_EXPORT, name: '导出台账', description: '允许导出台账数据', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_SUBMIT, name: '提交台账', description: '允许提交台账进入审批流程', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_APPROVE, name: '审批台账', description: '允许审批台账', group: '台账管理' },
        { key: PERMISSIONS.LEDGER_ADMIN_APPROVE, name: '管理员审批台账', description: '允许管理员审批台账', group: '台账管理' },
      ],
    },
    {
      name: '模板管理',
      permissions: [
        { key: PERMISSIONS.TEMPLATE_VIEW, name: '查看模板', description: '允许查看模板列表和详情', group: '模板管理' },
        { key: PERMISSIONS.TEMPLATE_CREATE, name: '创建模板', description: '允许创建新的模板', group: '模板管理' },
        { key: PERMISSIONS.TEMPLATE_EDIT, name: '编辑模板', description: '允许编辑现有模板', group: '模板管理' },
        { key: PERMISSIONS.TEMPLATE_DELETE, name: '删除模板', description: '允许删除模板', group: '模板管理' },
      ],
    },
    {
      name: '工作流管理',
      permissions: [
        { key: PERMISSIONS.WORKFLOW_VIEW, name: '查看工作流', description: '允许查看工作流列表和详情', group: '工作流管理' },
        { key: PERMISSIONS.WORKFLOW_CREATE, name: '创建工作流', description: '允许创建新的工作流', group: '工作流管理' },
        { key: PERMISSIONS.WORKFLOW_EDIT, name: '编辑工作流', description: '允许编辑现有工作流', group: '工作流管理' },
        { key: PERMISSIONS.WORKFLOW_DELETE, name: '删除工作流', description: '允许删除工作流', group: '工作流管理' },
      ],
    },
    {
      name: '审批管理',
      permissions: [
        { key: PERMISSIONS.APPROVAL_VIEW, name: '查看审批', description: '允许查看审批任务', group: '审批管理' },
        { key: PERMISSIONS.APPROVAL_SUBMIT, name: '提交审批', description: '允许提交审批', group: '审批管理' },
        { key: PERMISSIONS.APPROVAL_APPROVE, name: '批准审批', description: '允许批准审批', group: '审批管理' },
        { key: PERMISSIONS.APPROVAL_REJECT, name: '拒绝审批', description: '允许拒绝审批', group: '审批管理' },
      ],
    },
    {
      name: '用户管理',
      permissions: [
        { key: PERMISSIONS.USER_VIEW, name: '查看用户', description: '允许查看用户列表和详情', group: '用户管理' },
        { key: PERMISSIONS.USER_CREATE, name: '创建用户', description: '允许创建新的用户', group: '用户管理' },
        { key: PERMISSIONS.USER_EDIT, name: '编辑用户', description: '允许编辑现有用户', group: '用户管理' },
        { key: PERMISSIONS.USER_DELETE, name: '删除用户', description: '允许删除用户', group: '用户管理' },
      ],
    },
    {
      name: '角色管理',
      permissions: [
        { key: PERMISSIONS.ROLE_VIEW, name: '查看角色', description: '允许查看角色列表和详情', group: '角色管理' },
        { key: PERMISSIONS.ROLE_CREATE, name: '创建角色', description: '允许创建新的角色', group: '角色管理' },
        { key: PERMISSIONS.ROLE_EDIT, name: '编辑角色', description: '允许编辑现有角色', group: '角色管理' },
        { key: PERMISSIONS.ROLE_DELETE, name: '删除角色', description: '允许删除角色', group: '角色管理' },
      ],
    },
    {
      name: '团队管理',
      permissions: [
        { key: PERMISSIONS.TEAM_VIEW, name: '查看团队', description: '允许查看团队列表和详情', group: '团队管理' },
        { key: PERMISSIONS.TEAM_CREATE, name: '创建团队', description: '允许创建新的团队', group: '团队管理' },
        { key: PERMISSIONS.TEAM_EDIT, name: '编辑团队', description: '允许编辑现有团队', group: '团队管理' },
        { key: PERMISSIONS.TEAM_DELETE, name: '删除团队', description: '允许删除团队', group: '团队管理' },
      ],
    },
    {
      name: '字段管理',
      permissions: [
        { key: PERMISSIONS.FIELD_VIEW, name: '查看字段', description: '允许查看字段列表和详情', group: '字段管理' },
        { key: PERMISSIONS.FIELD_CREATE, name: '创建字段', description: '允许创建新的字段', group: '字段管理' },
        { key: PERMISSIONS.FIELD_EDIT, name: '编辑字段', description: '允许编辑现有字段', group: '字段管理' },
        { key: PERMISSIONS.FIELD_DELETE, name: '删除字段', description: '允许删除字段', group: '字段管理' },
      ],
    },
    {
      name: '权限管理',
      permissions: [
        { key: PERMISSIONS.PERMISSION_VIEW, name: '查看权限', description: '允许查看系统权限', group: '权限管理' },
        { key: PERMISSIONS.PERMISSION_ASSIGN, name: '分配权限', description: '允许分配系统权限', group: '权限管理' },
      ],
    },
    {
      name: '日志管理',
      permissions: [
        { key: PERMISSIONS.LOG_VIEW, name: '查看日志', description: '允许查看系统日志', group: '日志管理' },
      ],
    },
  ];
};

// 获取简化的权限组列表（用于RoleManagement组件）
export const getPermissionGroupsSimple = (): PermissionGroupSimple[] => {
  return [
    {
      groupName: '台账管理',
      permissions: [
        { key: PERMISSIONS.LEDGER_VIEW, label: '查看台账' },
        { key: PERMISSIONS.LEDGER_CREATE, label: '创建台账' },
        { key: PERMISSIONS.LEDGER_EDIT, label: '编辑台账' },
        { key: PERMISSIONS.LEDGER_DELETE, label: '删除台账' },
        { key: PERMISSIONS.LEDGER_EXPORT, label: '导出台账' },
        { key: PERMISSIONS.LEDGER_SUBMIT, label: '提交台账' },
        { key: PERMISSIONS.LEDGER_APPROVE, label: '审批台账' },
        { key: PERMISSIONS.LEDGER_ADMIN_APPROVE, label: '管理员审批台账' },
      ],
    },
    {
      groupName: '模板管理',
      permissions: [
        { key: PERMISSIONS.TEMPLATE_VIEW, label: '查看模板' },
        { key: PERMISSIONS.TEMPLATE_CREATE, label: '创建模板' },
        { key: PERMISSIONS.TEMPLATE_EDIT, label: '编辑模板' },
        { key: PERMISSIONS.TEMPLATE_DELETE, label: '删除模板' },
      ],
    },
    {
      groupName: '工作流管理',
      permissions: [
        { key: PERMISSIONS.WORKFLOW_VIEW, label: '查看工作流' },
        { key: PERMISSIONS.WORKFLOW_CREATE, label: '创建工作流' },
        { key: PERMISSIONS.WORKFLOW_EDIT, label: '编辑工作流' },
        { key: PERMISSIONS.WORKFLOW_DELETE, label: '删除工作流' },
      ],
    },
    {
      groupName: '审批管理',
      permissions: [
        { key: PERMISSIONS.APPROVAL_VIEW, label: '查看审批' },
        { key: PERMISSIONS.APPROVAL_SUBMIT, label: '提交审批' },
        { key: PERMISSIONS.APPROVAL_APPROVE, label: '批准审批' },
        { key: PERMISSIONS.APPROVAL_REJECT, label: '拒绝审批' },
      ],
    },
    {
      groupName: '用户管理',
      permissions: [
        { key: PERMISSIONS.USER_VIEW, label: '查看用户' },
        { key: PERMISSIONS.USER_CREATE, label: '创建用户' },
        { key: PERMISSIONS.USER_EDIT, label: '编辑用户' },
        { key: PERMISSIONS.USER_DELETE, label: '删除用户' },
      ],
    },
    {
      groupName: '角色管理',
      permissions: [
        { key: PERMISSIONS.ROLE_VIEW, label: '查看角色' },
        { key: PERMISSIONS.ROLE_CREATE, label: '创建角色' },
        { key: PERMISSIONS.ROLE_EDIT, label: '编辑角色' },
        { key: PERMISSIONS.ROLE_DELETE, label: '删除角色' },
      ],
    },
    {
      groupName: '团队管理',
      permissions: [
        { key: PERMISSIONS.TEAM_VIEW, label: '查看团队' },
        { key: PERMISSIONS.TEAM_CREATE, label: '创建团队' },
        { key: PERMISSIONS.TEAM_EDIT, label: '编辑团队' },
        { key: PERMISSIONS.TEAM_DELETE, label: '删除团队' },
      ],
    },
    {
      groupName: '字段管理',
      permissions: [
        { key: PERMISSIONS.FIELD_VIEW, label: '查看字段' },
        { key: PERMISSIONS.FIELD_CREATE, label: '创建字段' },
        { key: PERMISSIONS.FIELD_EDIT, label: '编辑字段' },
        { key: PERMISSIONS.FIELD_DELETE, label: '删除字段' },
      ],
    },
    {
      groupName: '权限管理',
      permissions: [
        { key: PERMISSIONS.PERMISSION_VIEW, label: '查看权限' },
        { key: PERMISSIONS.PERMISSION_ASSIGN, label: '分配权限' },
      ],
    },
    {
      groupName: '日志管理',
      permissions: [
        { key: PERMISSIONS.LOG_VIEW, label: '查看日志' },
      ],
    },
  ];
};

// 获取拍平的所有权限列表
export const getAllPermissions = (): Permission[] => {
  const permGroups = getPermissionGroups();
  const allPermissions: Permission[] = [];
  
  permGroups.forEach(group => {
    group.permissions.forEach(perm => {
      allPermissions.push(perm);
    });
  });
  
  return allPermissions;
}; 