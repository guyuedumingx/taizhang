import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Modal, Form, Select, message, Popconfirm, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { Team, TeamCreate, TeamUpdate, User } from '../../types';
import { TeamService } from '../../services/TeamService';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import useDepartments from '../../hooks/useDepartments';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

const TeamManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [editingTeamId, setEditingTeamId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const { options: departmentOptions, filters: departmentFilters } = useDepartments();

  // 获取团队和用户数据
  const fetchData = async () => {
    if (!hasPermission(PERMISSIONS.TEAM_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    setLoading(true);
    try {
      const [teamsData, usersData] = await Promise.all([
        TeamService.getTeams(),
        TeamService.getUsers()
      ]);
      
      setTeams(teamsData);
      setUsers(usersData);
    } catch (error) {
      console.error('获取数据失败:', error);
      message.error('获取数据失败，请刷新页面重试');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载数据
  useEffect(() => {
    fetchData();
  }, [hasPermission]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const showAddModal = () => {
    form.resetFields();
    setModalTitle('添加团队');
    setEditingTeamId(null);
    setIsModalVisible(true);
  };

  const showEditModal = (team: Team) => {
    form.setFieldsValue({
      name: team.name || '',
      department: team.department || '',
      description: team.description || '',
      leader_id: team.leader_id,
    });
    setModalTitle('编辑团队');
    setEditingTeamId(team.id);
    setIsModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      if (editingTeamId) {
        // 编辑团队
        await TeamService.updateTeam(editingTeamId, values as TeamUpdate);
        message.success('团队更新成功');
      } else {
        // 添加团队
        await TeamService.createTeam(values as TeamCreate);
        message.success('团队添加成功');
      }
      
      setIsModalVisible(false);
      fetchData(); // 重新获取数据以刷新列表
    } catch (error) {
      console.error('操作失败:', error);
      message.error('操作失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      setLoading(true);
      await TeamService.deleteTeam(id);
      message.success('团队删除成功');
      fetchData(); // 重新获取数据以刷新列表
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const filteredTeams = teams.filter(team => 
    (team.name || '').toLowerCase().includes(searchText.toLowerCase()) ||
    (team.department || '').toLowerCase().includes(searchText.toLowerCase()) ||
    (team.description && team.description.toLowerCase().includes(searchText.toLowerCase())) ||
    (team.leader_name && team.leader_name.toLowerCase().includes(searchText.toLowerCase()))
  );

  const columns: ColumnsType<Team> = [
    {
      title: '团队名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => (a.name || '').localeCompare(b.name || ''),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      filters: departmentFilters,
      onFilter: (value, record) => (record.department || '') === value.toString(),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '团队负责人',
      dataIndex: 'leader_name',
      key: 'leader_name',
      render: (leader_name: string | null | undefined) => leader_name || <Tag color="warning">未指定</Tag>,
    },
    {
      title: '成员数量',
      dataIndex: 'member_count',
      key: 'member_count',
      sorter: (a, b) => a.member_count - b.member_count,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<UserOutlined />}
            onClick={() => navigate(`/dashboard/admin/teams/${record.id}/members`)}
            disabled={!hasPermission(PERMISSIONS.TEAM_VIEW)}
            title="查看成员"
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
            disabled={!hasPermission(PERMISSIONS.TEAM_EDIT)}
          />
          <Popconfirm
            title="确定要删除这个团队吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.TEAM_DELETE)}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.TEAM_DELETE)}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
    <BreadcrumbNav 
        items={[
          { title: '系统管理', path: '/dashboard/admin' },
          { title: '团队管理', path: '/dashboard/admin/teams' }
        ]}
        showBackButton={false}
      />
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>团队管理</Title>
          <Space>
            <Search
              placeholder="搜索团队"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showAddModal}
              disabled={!hasPermission(PERMISSIONS.TEAM_CREATE)}
            >
              添加团队
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredTeams}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      <Modal
        title={modalTitle}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
        destroyOnClose
        confirmLoading={loading}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="团队名称"
            name="name"
            rules={[{ required: true, message: '请输入团队名称' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="部门"
            name="department"
            rules={[{ required: true, message: '请选择部门' }]}
          >
            <Select placeholder="选择部门">
              {departmentOptions.map((option) => (
                <Option key={option.value} value={option.value}>{option.label}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入描述' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          
          <Form.Item
            label="团队负责人"
            name="leader_id"
          >
            <Select allowClear placeholder="选择负责人">
              {loading ? (
                <Option value="" disabled>加载中...</Option>
              ) : users && Array.isArray(users) ? (
                users
                  .filter(user => {
                    // 如果正在编辑团队，不过滤部门
                    if (editingTeamId) return true;
                    
                    // 获取当前部门值
                    const departmentValue = form.getFieldValue('department');
                    // 只有当部门存在且匹配时才显示相应用户
                    return !departmentValue || !user.department || user.department === departmentValue;
                  })
                  .map(user => (
                    <Option key={user.id} value={user.id}>
                      {user.name || user.username} {user.department ? `(${user.department})` : ''}
                    </Option>
                  ))
              ) : (
                <Option value="" disabled>暂无数据</Option>
              )}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
    </>
  );
};

export default TeamManagement; 