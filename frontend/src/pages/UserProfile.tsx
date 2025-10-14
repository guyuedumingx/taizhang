import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Avatar, Button, Form, Input, Select, message, Divider, Spin } from 'antd';
import { UserOutlined, EditOutlined, SaveOutlined, CloseOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { UserService } from '../services/UserService';
import BreadcrumbNav from '../components/common/BreadcrumbNav';
import { User, UserUpdate } from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

const UserProfile: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [editing, setEditing] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [refreshingPermissions, setRefreshingPermissions] = useState<boolean>(false);
  const [userInfo, setUserInfo] = useState<User | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { user, updatePermissions } = useAuthStore();

  useEffect(() => {
    fetchUserDetails();
  }, []);

  const fetchUserDetails = async () => {
    if (!user || !user.id) {
      message.error('未获取到用户信息');
      navigate('/dashboard');
      return;
    }

    setLoading(true);
    try {
      const userData = await UserService.getUser(user.id);
      setUserInfo(userData);
      form.setFieldsValue({
        name: userData.name,
        department: userData.department,
        ehr_id: userData.ehr_id,
      });
    } catch (error) {
      console.error('获取用户信息失败:', error);
      message.error('获取用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
  };

  const handleCancelEdit = () => {
    setEditing(false);
    if (userInfo) {
      form.setFieldsValue({
        name: userInfo.name,
        department: userInfo.department,
        ehr_id: userInfo.ehr_id,
      });
    }
  };

  const handleSave = async () => {
    if (!userInfo || !user || !user.id) return;

    try {
      await form.validateFields();
      const values = form.getFieldsValue();
      
      setSaving(true);
      const updatedUser = await UserService.updateUser(user.id, values as UserUpdate);
      
      setUserInfo(updatedUser);
      setEditing(false);
      message.success('用户信息更新成功');
    } catch (error) {
      console.error('更新用户信息失败:', error);
      message.error('更新用户信息失败');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = () => {
    // 可以在此添加修改密码的弹窗或跳转到修改密码页面
    message.info('密码修改功能即将推出');
  };

  const handleRefreshPermissions = async () => {
    setRefreshingPermissions(true);
    try {
      await updatePermissions();
      message.success('权限刷新成功');
    } catch (error) {
      console.error('刷新权限失败:', error);
      message.error('刷新权限失败');
    } finally {
      setRefreshingPermissions(false);
    }
  };

  if (loading) {
    return (
      <>
        <BreadcrumbNav
          items={[
            { title: '个人中心', path: '/dashboard/profile' }
          ]}
          showBackButton={false}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        </Card>
      </>
    );
  }

  if (!userInfo) {
    return (
      <>
        <BreadcrumbNav
          items={[
            { title: '个人中心', path: '/dashboard/profile' }
          ]}
          showBackButton={false}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Text type="danger">未找到用户信息</Text>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <BreadcrumbNav
        items={[
          { title: '个人中心', path: '/dashboard/profile' }
        ]}
        showBackButton={false}
      />
      
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={4}>个人信息</Title>
          {!editing ? (
            <Button 
              type="primary" 
              icon={<EditOutlined />} 
              onClick={handleEdit}
            >
              编辑资料
            </Button>
          ) : (
            <div>
              <Button 
                type="primary" 
                icon={<SaveOutlined />} 
                onClick={handleSave} 
                loading={saving} 
                style={{ marginRight: 8 }}
              >
                保存
              </Button>
              <Button 
                icon={<CloseOutlined />} 
                onClick={handleCancelEdit}
              >
                取消
              </Button>
            </div>
          )}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <div style={{ marginRight: 24 }}>
            <Avatar 
              size={120} 
              icon={<UserOutlined />} 
              style={{ backgroundColor: '#1890ff', marginBottom: 16 }}
            />
          </div>
          
          <div style={{ flex: 1 }}>
            {!editing ? (
              <Descriptions bordered column={2} size="middle">
                <Descriptions.Item label="用户名" span={2}>{userInfo.username}</Descriptions.Item>
                <Descriptions.Item label="姓名">{userInfo.name}</Descriptions.Item>
                <Descriptions.Item label="所属部门">{userInfo.department}</Descriptions.Item>
                <Descriptions.Item label="EHR编号">{userInfo.ehr_id}</Descriptions.Item>
                <Descriptions.Item label="所属团队">{userInfo.team_id ? `团队ID: ${userInfo.team_id}` : '未分配团队'}</Descriptions.Item>
                <Descriptions.Item label="账号状态" span={2}>
                  {userInfo.is_active ? (
                    <Text type="success">激活</Text>
                  ) : (
                    <Text type="danger">禁用</Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="系统角色" span={2}>
                  {(userInfo.roles || []).map(role => (
                    <Text key={role} style={{ marginRight: 8 }}>{role}</Text>
                  ))}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Form
                form={form}
                layout="vertical"
                initialValues={{
                  name: userInfo.name,
                  department: userInfo.department,
                  ehr_id: userInfo.ehr_id,
                }}
              >
                <Form.Item
                  label="用户名"
                >
                  <Input value={userInfo.username || ''} disabled />
                </Form.Item>
                
                <Form.Item
                  name="name"
                  label="姓名"
                  rules={[{ required: true, message: '请输入姓名' }]}
                >
                  <Input />
                </Form.Item>
                
                <Form.Item
                  name="department"
                  label="所属部门"
                  rules={[{ required: true, message: '请选择部门' }]}
                >
                  <Select>
                    <Option value="财务部">财务部</Option>
                    <Option value="生产部">生产部</Option>
                    <Option value="客服部">客服部</Option>
                    <Option value="设备部">设备部</Option>
                  </Select>
                </Form.Item>
                
                <Form.Item
                  name="ehr_id"
                  label="EHR编号"
                  rules={[{ required: true, message: '请输入EHR编号' }]}
                >
                  <Input disabled />
                </Form.Item>
              </Form>
            )}
            
            <Divider />
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Title level={4}>权限管理</Title>
              <Button 
                icon={<ReloadOutlined />} 
                loading={refreshingPermissions}
                onClick={handleRefreshPermissions}
              >
                刷新权限
              </Button>
            </div>
            
            {user?.permissions && (
              <Descriptions column={1} bordered style={{ marginTop: 16 }}>
                <Descriptions.Item label="当前拥有权限">
                  {user.permissions.join(', ')}
                </Descriptions.Item>
              </Descriptions>
            )}
            
            <div>
              <Button onClick={handlePasswordChange}>修改密码</Button>
            </div>
          </div>
        </div>
      </Card>
    </>
  );
};

export default UserProfile; 