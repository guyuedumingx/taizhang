import React, { useState, useEffect } from 'react';
import { Table, Card, Typography, Tag, Space, Collapse, Alert } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Panel } = Collapse;

interface Permission {
  key: string;
  name: string;
  description: string;
  group: string;
}

interface PermissionGroup {
  name: string;
  permissions: Permission[];
}

const PermissionManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.ROLE_VIEW)) {
      return;
    }

    // 获取权限列表
    setLoading(true);
    // 模拟获取权限列表
    setTimeout(() => {
      const groups: PermissionGroup[] = [
        {
          name: '台账管理',
          permissions: [
            { key: PERMISSIONS.LEDGER_VIEW, name: '查看台账', description: '允许查看台账列表和详情', group: '台账管理' },
            { key: PERMISSIONS.LEDGER_CREATE, name: '创建台账', description: '允许创建新的台账', group: '台账管理' },
            { key: PERMISSIONS.LEDGER_EDIT, name: '编辑台账', description: '允许编辑现有台账', group: '台账管理' },
            { key: PERMISSIONS.LEDGER_DELETE, name: '删除台账', description: '允许删除台账', group: '台账管理' },
            { key: PERMISSIONS.LEDGER_EXPORT, name: '导出台账', description: '允许导出台账数据', group: '台账管理' },
            { key: PERMISSIONS.LEDGER_APPROVE, name: '审批台账', description: '允许审批台账', group: '台账管理' },
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
      
      setPermissionGroups(groups);
      
      // 将所有权限放入一个数组中
      const allPerms: Permission[] = [];
      groups.forEach(group => {
        group.permissions.forEach(perm => {
          allPerms.push(perm);
        });
      });
      
      setAllPermissions(allPerms);
      setLoading(false);
    }, 1000);
  }, [hasPermission]);

  const columns: ColumnsType<Permission> = [
    {
      title: '权限标识',
      dataIndex: 'key',
      key: 'key',
    },
    {
      title: '权限名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '权限描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '所属分组',
      dataIndex: 'group',
      key: 'group',
      render: (group: string) => {
        const colorMap: Record<string, string> = {
          '台账管理': 'blue',
          '模板管理': 'green',
          '用户管理': 'purple',
          '角色管理': 'orange',
          '团队管理': 'cyan',
          '工作流管理': 'geekblue',
          '审批管理': 'volcano',
          '字段管理': 'gold',
          '权限管理': 'magenta',
          '日志管理': 'lime',
        };
        return <Tag color={colorMap[group] || 'default'}>{group}</Tag>;
      },
      filters: permissionGroups.map(group => ({ text: group.name, value: group.name })),
      onFilter: (value, record) => record.group === value,
    },
  ];

  if (!hasPermission(PERMISSIONS.ROLE_VIEW)) {
    return (
      <Card>
        <Alert
          message="权限不足"
          description="您没有权限访问此页面"
          type="error"
          showIcon
        />
      </Card>
    );
  }

  return (
    <div>
      <Card>
        <Title level={4}>权限管理</Title>
        
        <Alert
          message="系统权限说明"
          description="本页面展示了系统中所有可用的权限。权限是分配给角色的，用户通过所属角色获得相应的权限。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Space direction="vertical" style={{ width: '100%' }}>
          <Collapse defaultActiveKey={['1']}>
            <Panel header="按分组查看权限" key="1">
              {permissionGroups.map(group => (
                <div key={group.name} style={{ marginBottom: 16 }}>
                  <Title level={5}>{group.name}</Title>
                  <Table
                    columns={columns.filter(col => col.key !== 'group')}
                    dataSource={group.permissions}
                    rowKey="key"
                    pagination={false}
                    size="small"
                  />
                </div>
              ))}
            </Panel>
            <Panel header="所有权限列表" key="2">
              <Table
                columns={columns}
                dataSource={allPermissions}
                rowKey="key"
                loading={loading}
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }}
              />
            </Panel>
          </Collapse>
        </Space>
      </Card>
    </div>
  );
};

export default PermissionManagement; 