import React from 'react';
import { Form, Input, Select, Button, Space, Typography, Radio, Row, Col, Switch, message } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, DeleteOutlined } from '@ant-design/icons';
import { WorkflowNodeCreate, User, Role } from '../../types';
import ApproverSelector from './ApproverSelector';

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

const approveTypes = [
  { label: '任一审批人通过即可', value: 'any' },
  { label: '所有审批人必须通过', value: 'all' },
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

  // 处理审批人变更
  const handleApproversChange = (selectedIds: number | number[]) => {
    // 确保始终传递数组给onUpdate
    const ids = Array.isArray(selectedIds) ? selectedIds : [selectedIds];
    onUpdate(index, 'approver_ids', ids);
  };

  // 更新节点属性
  const handleUpdateNode = (index: number, field: string, value: unknown) => {
    try {
      onUpdate(index, field, value);
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('更新节点失败');
      }
    }
  };

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
            onChange={(value) => handleUpdateNode(index, 'node_type', value)}
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
            onChange={(e) => handleUpdateNode(index, 'name', e.target.value)}
            placeholder="请输入节点名称"
          />
        </Form.Item>

        <Form.Item label="节点描述" className="mb-2">
          <TextArea
            value={node.description}
            onChange={(e) => handleUpdateNode(index, 'description', e.target.value)}
            placeholder="请输入节点描述"
            rows={2}
          />
        </Form.Item>

        {isApproval && (
          <>
            <Form.Item label="审批角色" className="mb-2">
              <Select
                value={node.approver_role_id}
                onChange={(value) => handleUpdateNode(index, 'approver_role_id', value)}
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
              <Text type="secondary" style={{ fontSize: 12 }}>
                选择审批角色后，该角色下所有用户都可以审批。可与审批人一起使用。
              </Text>
            </Form.Item>

            <Form.Item label="审批人" className="mb-2">
              <ApproverSelector
                mode="multiple"
                value={node.approver_ids}
                onChange={handleApproversChange}
                allUsers={users}
                nodeId={0}
                label=""
              />
            </Form.Item>

            <Form.Item label="审批方式" className="mb-2">
              <Radio.Group
                options={approveTypes}
                value={node.multi_approve_type || 'any'}
                onChange={(e) => handleUpdateNode(index, 'multi_approve_type', e.target.value)}
              />
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {node.multi_approve_type === 'all' 
                    ? '需要所有选定的审批人都通过，才能进入下一节点' 
                    : '只需要任意一个审批人通过即可进入下一节点'}
                </Text>
              </div>
            </Form.Item>
          </>
        )}
      </Space>
    </div>
  );
};

export default WorkflowNodeComponent; 