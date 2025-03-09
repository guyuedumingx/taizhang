import React from 'react';
import { Form, Input, Select, Button, Space, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, DeleteOutlined } from '@ant-design/icons';
import { WorkflowNodeCreate, User, Role } from '../../types';

const { Option } = Select;
const { TextArea } = Input;
const { Text } = Typography;

interface NodeType {
  value: string;
  label: string;
}

const nodeTypes: NodeType[] = [
  { value: 'start', label: '开始节点' },
  { value: 'approval', label: '审批节点' },
  { value: 'end', label: '结束节点' },
];

interface WorkflowNodeComponentProps {
  node: WorkflowNodeCreate;
  index: number;
  roles: Role[];
  users: User[];
  totalNodes: number;
  onDelete: (index: number) => void;
  onMove: (index: number, direction: 'up' | 'down') => void;
  onUpdate: (index: number, field: string, value: unknown) => void;
}

const WorkflowNodeComponent: React.FC<WorkflowNodeComponentProps> = ({
  node,
  index,
  roles,
  users,
  totalNodes,
  onDelete,
  onMove,
  onUpdate,
}) => {
  const isStart = node.node_type === 'start';
  const isEnd = node.node_type === 'end';
  const isApproval = node.node_type === 'approval';
  const isFirst = index === 0;
  const isLast = index === totalNodes - 1;

  return (
    <div className="workflow-node" style={{ marginBottom: 16, padding: 16, border: '1px solid #f0f0f0', borderRadius: 4, background: '#fafafa' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Text strong>节点 {index + 1}</Text>
          <Space>
            <Button
              type="text"
              icon={<ArrowUpOutlined />}
              disabled={isFirst || isStart}
              onClick={() => onMove(index, 'up')}
              title="上移节点"
            />
            <Button
              type="text"
              icon={<ArrowDownOutlined />}
              disabled={isLast || isEnd}
              onClick={() => onMove(index, 'down')}
              title="下移节点"
            />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={isStart || isEnd}
              onClick={() => onDelete(index)}
              title="删除节点"
            />
          </Space>
        </div>

        <Form.Item label="节点类型" className="mb-2">
          <Select
            value={node.node_type}
            disabled={isStart || isEnd}
            onChange={(value) => onUpdate(index, 'node_type', value)}
            style={{ width: '100%' }}
          >
            {nodeTypes.map((type) => (
              <Option key={type.value} value={type.value}>
                {type.label}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="节点名称" className="mb-2">
          <Input
            value={node.name}
            onChange={(e) => onUpdate(index, 'name', e.target.value)}
            placeholder="请输入节点名称"
          />
        </Form.Item>

        <Form.Item label="节点描述" className="mb-2">
          <TextArea
            value={node.description}
            onChange={(e) => onUpdate(index, 'description', e.target.value)}
            placeholder="请输入节点描述"
            rows={2}
          />
        </Form.Item>

        {isApproval && (
          <>
            <Form.Item label="审批角色" className="mb-2">
              <Select
                value={node.approver_role_id}
                onChange={(value) => onUpdate(index, 'approver_role_id', value)}
                placeholder="请选择审批角色"
                allowClear
                style={{ width: '100%' }}
              >
                {roles.map((role) => (
                  <Option key={role.id} value={role.id}>
                    {role.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item label="审批人" className="mb-2">
              <Select
                value={node.approver_user_id}
                onChange={(value) => onUpdate(index, 'approver_user_id', value)}
                placeholder="请选择审批人"
                allowClear
                style={{ width: '100%' }}
              >
                {users.map((user) => (
                  <Option key={user.id} value={user.id}>
                    {user.name} ({user.username})
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </>
        )}
      </Space>
    </div>
  );
};

export default WorkflowNodeComponent; 