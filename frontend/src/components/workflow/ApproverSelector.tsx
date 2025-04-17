import React, { useState, useEffect, useCallback } from 'react';
import { Form, Select, Typography, Spin, Empty } from 'antd';
import { User } from '../../types';
import { WorkflowService } from '../../services/WorkflowService';

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
  allUsers?: User[] | { items: User[]; total: number }; // 支持数组或分页对象
  disabled?: boolean;
}

const ApproverSelector: React.FC<ApproverSelectorProps> = ({
  nodeId,
  onChange,
  value,
  style,
  mode = 'single', // 提供默认值，避免undefined
  required = true,
  label = '选择审批人',
  allUsers,
  disabled = false
}) => {
  const [loading, setLoading] = useState(false);
  const [approvers, setApprovers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [localValue, setLocalValue] = useState<number | number[] | undefined>(value);

  // 确保值的一致性，用于调试
  useEffect(() => {
    if (value !== localValue) {
      setLocalValue(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // 从props解析用户列表，确保类型正确
  const processUserOptions = useCallback(() => {
    if (!allUsers) return [];
    if (Array.isArray(allUsers)) return allUsers;
    if (allUsers && 'items' in allUsers && Array.isArray(allUsers.items)) {
      return allUsers.items;
    }
    return [];
  }, [allUsers]);

  useEffect(() => {
    // 如果提供了allUsers，使用它而不是从后端获取
    if (allUsers) {
      setApprovers(processUserOptions());
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
        const data = await WorkflowService.getNodeApprovers(nodeId);
      
        setApprovers(data);
        
        // 只在初始时自动选择，避免覆盖用户选择
        if (data.length > 0 && value === undefined) {
          if (mode === 'single') {
            // 单选模式：选择第一个审批人
            const firstId = String(data[0].id);
            onChange(Number(firstId)); // 确保ID是数字
          } else if (mode === 'multiple') {
            // 多选模式：默认选择所有审批人
            const allIds = data.map((user: User) => Number(String(user.id))); // 确保ID是数字
            onChange(allIds);
          }
        }
      } finally {
        setLoading(false);
      }
    };
    
    fetchApprovers();
  // 移除可能导致循环渲染的依赖项
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId, allUsers]);

  // 安全地处理值变更，确保类型一致性
  const handleChange = (selectedValue: number | number[]) => {
    setLocalValue(selectedValue);
    
    // 确保返回给父组件的值类型正确
    if (mode === 'multiple') {
      // 确保多选模式返回数组
      if (Array.isArray(selectedValue)) {
        onChange(selectedValue.map(id => Number(id))); // 确保所有ID都是数字
      } else if (selectedValue !== undefined) {
        onChange([Number(selectedValue)]); // 如果只选了一个，包装为数组
      } else {
        onChange([]); // 未选择时返回空数组
      }
    } else {
      // 单选模式直接返回数字ID
      onChange(selectedValue !== undefined ? Number(selectedValue) : undefined);
    }
  };

  if (loading && !allUsers) {
    return <Spin size="small" tip="加载审批人列表..." />;
  }

  if (error && !allUsers) {
    return <Text type="danger">{error}</Text>;
  }

  // 获取可用的用户选项
  // TODO 后续测试时需要改成审批人，现在是审批人跟所有用户二选一
  const userOptions = allUsers ? processUserOptions() : approvers;
  
  // 确保userOptions是数组
  const safeUserOptions = Array.isArray(userOptions) ? userOptions : [];
  
  if (safeUserOptions.length === 0 && !allUsers) {
    return <Empty description="此节点没有可用的审批人" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  // 单选模式且只有一个选项时，直接显示审批人名称
  if (safeUserOptions.length === 1 && mode === 'single' && !allUsers) {
    return (
      <div style={style}>
        <Text>审批人: {safeUserOptions[0].name}</Text>
      </div>
    );
  }

  // 确保value是正确的类型
  let selectValue = localValue;
  if (mode === 'multiple' && selectValue !== undefined) {
    // 确保多选模式下value是数组
    selectValue = Array.isArray(selectValue) ? selectValue : [selectValue];
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
        value={selectValue}
        style={{ width: '100%' }}
        mode={mode === 'multiple' ? 'multiple' : undefined}
        showSearch
        optionFilterProp="children"
        disabled={disabled}
      >
        {safeUserOptions.map(user => (
          <Option key={user.id} value={Number(user.id)}>
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