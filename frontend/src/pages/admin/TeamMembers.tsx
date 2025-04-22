import React, { useState, useEffect } from 'react';
import { Card, Table, Typography, Space, Button, Tag, message, Spin } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { TeamService } from '../../services/TeamService';
import { User, Team } from '../../types';
import { getDepartmentColorByName } from '../../utils/DepartmentGroups';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const TeamMembers: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [team, setTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<User[]>([]);

  useEffect(() => {
    if (!id) {
      message.error('团队ID无效');
      navigate('/dashboard/admin/teams');
      return;
    }

    if (!hasPermission(PERMISSIONS.TEAM_VIEW)) {
      message.error('您没有查看团队的权限');
      navigate('/dashboard');
      return;
    }

    fetchTeamAndMembers(parseInt(id));
  }, [id, hasPermission, navigate]);

  const fetchTeamAndMembers = async (teamId: number) => {
    setLoading(true);
    try {
      const [teamData, membersData] = await Promise.all([
        TeamService.getTeam(teamId),
        TeamService.getTeamMembers(teamId)
      ]);

      setTeam(teamData);
      setMembers(membersData);
    } catch (error) {
      console.error('获取团队成员失败:', error);
      message.error('获取团队成员失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<User> = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'EHR ID',
      dataIndex: 'ehr_id',
      key: 'ehr_id',
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (department: string) => department ? (
        <Tag color={getDepartmentColorByName(department)}>
          {department}
        </Tag>
      ) : '-',
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[] | undefined) => (
        <Space size={[0, 4]} wrap>
          {roles && roles.length > 0 ? (
            roles.map(role => (
              <Tag key={role} color={role === 'admin' ? 'red' : role === 'manager' ? 'orange' : 'default'}>
                {role}
              </Tag>
            ))
          ) : (
            <span>-</span>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '启用' : '停用'}
        </Tag>
      ),
    },
  ];

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>加载中...</div>
        </div>
      </Card>
    );
  }

  if (!team) {
    return <Card><Typography.Text>团队不存在或已被删除</Typography.Text></Card>;
  }

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/dashboard/admin/teams')}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>{team.name} - 团队成员</Title>
        </Space>
      </div>
      
      <Table
        columns={columns}
        dataSource={members}
        rowKey="id"
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
      />
    </Card>
  );
};

export default TeamMembers; 