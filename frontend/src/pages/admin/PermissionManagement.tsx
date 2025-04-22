import React, { useState, useEffect } from 'react';
import { Table, Card, Typography, Tag, Space, Collapse, Alert } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';
import { Permission, PermissionGroup, getPermissionGroups, getAllPermissions } from '../../utils/PermissionGroups';

const { Title } = Typography;
const { Panel } = Collapse;

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
    // 使用统一的权限组管理模块获取权限数据
    setTimeout(() => {
      const groups = getPermissionGroups();
      setPermissionGroups(groups);
      
      // 将所有权限放入一个数组中
      const allPerms = getAllPermissions();
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
                  defaultPageSize: 10,
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