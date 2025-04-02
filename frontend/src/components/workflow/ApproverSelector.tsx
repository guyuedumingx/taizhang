import React, { useState, useEffect } from 'react';
import { Form, Select, Typography, Spin, Empty } from 'antd';
import { User } from '../../types';
import axios, { AxiosError } from 'axios';
import { API_BASE_URL } from '../../config';

const { Text } = Typography;
const { Option } = Select;

interface ApproverSelectorProps {
  nodeId: number;
  onChange: (approverId: number | number[]) => void;
  value?: number | number[];
  style?: React.CSSProperties;
  mode?: 'single' | 'multiple';
  required?: boolean;
  label?: string;
  allUsers?: User[]; // 用于工作流编辑时提供所有可选用户
  disabled?: boolean;
}

const ApproverSelector: React.FC<ApproverSelectorProps> = ({
  nodeId,
  onChange,
  value,
  style,
  mode = 'single',
  required = true,
  label = '选择审批人',
  allUsers,
  disabled = false
}) => {
  const [loading, setLoading] = useState(false);
  const [approvers, setApprovers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 如果提供了allUsers数组，使用它而不是从后端获取
    if (allUsers) {
      setApprovers(allUsers);
      return;
    }
    
    // 如果nodeId为0或不存在，说明是新节点，不需要获取审批人
    if (!nodeId || nodeId <= 0) {
      setApprovers([]);
      return;
    }
    
    const fetchApprovers = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log(`正在获取节点ID=${nodeId}的审批人...`);
        const token = localStorage.getItem('auth-storage')
          ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token
          : null;
          
        if (!token) {
          console.error('未找到认证Token');
          setError('认证失败：未找到有效的Token');
          setLoading(false);
          return;
        }
        
        const apiUrl = `${API_BASE_URL}/workflow-nodes/${nodeId}/approvers`;
        console.log(`请求URL: ${apiUrl}`);
        
        const response = await axios.get(apiUrl, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        
        console.log('获取审批人成功:', response.data);
        setApprovers(response.data);
        
        // 如果审批人列表非空但当前没有选择值，根据模式自动选择
        if (response.data.length > 0 && !value) {
          if (mode === 'single') {
            // 单选模式：选择第一个审批人
            onChange(response.data[0].id);
          } else if (mode === 'multiple') {
            // 多选模式：默认选择所有审批人
            const allIds = response.data.map((user: User) => user.id);
            onChange(allIds);
          }
        }
      } catch (err) {
        console.error('获取审批人失败:', err);
        if (axios.isAxiosError(err)) {
          const axiosError = err as AxiosError;
          console.error('错误状态码:', axiosError.response?.status);
          console.error('错误详情:', axiosError.response?.data);
          
          // 处理404错误（节点可能是新创建的，还没有审批人）
          if (axiosError.response?.status === 404) {
            setApprovers([]);
            return;
          }
        }
        setError('无法获取审批人列表，请检查网络连接或联系管理员');
      } finally {
        setLoading(false);
      }
    };
    
    fetchApprovers();
  }, [nodeId, onChange, value, mode, allUsers]);

  const handleChange = (selectedValue: number | number[]) => {
    onChange(selectedValue);
  };

  if (loading && !allUsers) {
    return <Spin size="small" tip="加载审批人列表..." />;
  }

  if (error && !allUsers) {
    return <Text type="danger">{error}</Text>;
  }

  // 工作流编辑模式或从后端获取的审批人
  const userOptions = allUsers || approvers;
  
  if (userOptions.length === 0 && !allUsers) {
    return <Empty description="此节点没有可用的审批人" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  // 单选模式且只有一个选项时，直接显示审批人名称
  if (userOptions.length === 1 && mode === 'single' && !allUsers) {
    return (
      <div style={style}>
        <Text>审批人: {userOptions[0].name}</Text>
      </div>
    );
  }

  return (
    <Form.Item
      label={label}
      required={required}
      style={style}
    >
      <Select
        placeholder={`请选择${mode === 'multiple' ? '一个或多个' : ''}审批人`}
        onChange={handleChange}
        value={value}
        style={{ width: '100%' }}
        mode={mode === 'multiple' ? 'multiple' : undefined}
        showSearch
        optionFilterProp="children"
        disabled={disabled}
      >
        {userOptions.map(user => (
          <Option key={user.id} value={user.id}>
            {user.name} ({user.username})
          </Option>
        ))}
      </Select>
      {mode === 'multiple' && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          可以选择多个审批人，多个审批人时可以选择审批方式（任一审批或全部审批）。
        </Text>
      )}
    </Form.Item>
  );
};

export default ApproverSelector; 