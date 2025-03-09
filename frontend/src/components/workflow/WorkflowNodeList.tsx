import React from 'react';
import { Button, Divider, List, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { WorkflowNodeCreate, User, Role } from '../../types';
import WorkflowNodeComponent from './WorkflowNodeComponent';

const { Title } = Typography;

interface WorkflowNodeListProps {
  nodes: WorkflowNodeCreate[];
  roles: Role[];
  users: User[];
  onAddNode: () => void;
  onDeleteNode: (index: number) => void;
  onMoveNode: (index: number, direction: 'up' | 'down') => void;
  onUpdateNode: (index: number, field: string, value: unknown) => void;
}

const WorkflowNodeList: React.FC<WorkflowNodeListProps> = ({
  nodes,
  roles,
  users,
  onAddNode,
  onDeleteNode,
  onMoveNode,
  onUpdateNode,
}) => {
  return (
    <div className="workflow-node-list">
      <Divider>
        <Title level={4}>工作流节点配置</Title>
      </Divider>
      
      <List
        dataSource={nodes}
        renderItem={(node, index) => (
          <List.Item key={index} style={{ display: 'block', padding: 0 }}>
            <WorkflowNodeComponent 
              node={node}
              index={index}
              roles={roles}
              users={users}
              totalNodes={nodes.length}
              onDelete={onDeleteNode}
              onMove={onMoveNode}
              onUpdate={onUpdateNode}
            />
          </List.Item>
        )}
        footer={
          <div style={{ textAlign: 'center' }}>
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={onAddNode}
              style={{ width: '60%' }}
            >
              添加审批节点
            </Button>
            <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
              提示：审批节点将被添加到结束节点之前
            </div>
          </div>
        }
      />
    </div>
  );
};

export default WorkflowNodeList; 