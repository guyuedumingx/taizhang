/**
 * P7 创建提交 Modal (B1 专项工作 + A2 档案修改 + A3 亮点标签 三合一)
 */
import React from 'react';
import {
  Modal,
  Tabs,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
} from 'antd';
import * as PortraitAPI from '../../api/portrait';

const { TextArea } = Input;

const TAB_ITEMS = [
  { key: 'special_work', label: '专项工作 (B1)' },
  { key: 'profile_edit', label: '档案修改 (A2)' },
  { key: 'skill_tag_edit', label: '亮点标签 (A3)' },
];

// 审批人下拉 (从 /users 拉取活跃用户)
const ApproverSelect: React.FC<{ value?: number; onChange?: (v: number) => void; disabled?: boolean }> = ({ value, onChange, disabled }) => {
  const [users, setUsers] = React.useState<{ id: number; name: string; ehr_id: string }[]>([]);
  React.useEffect(() => {
    (async () => {
      try {
        const data = await PortraitAPI.listUsersForApprover({ limit: 200 });
        setUsers(data.items || []);
      } catch {
        // 失败时静默
      }
    })();
  }, []);
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={disabled}
      placeholder="选择审批人 (本组组长 / 管理员)"
      showSearch
      optionFilterProp="children"
    >
      {users.map((u) => (
        <Select.Option key={u.id} value={u.id}>
          {u.name} ({u.ehr_id})
        </Select.Option>
      ))}
    </Select>
  );
};

// 三类表单字段配置
const SPECIAL_WORK_FIELDS = (
  <>
    <Form.Item
      name="project_name"
      label="项目名"
      rules={[{ required: true, message: '请填写项目名' }, { max: 100 }]}
    >
      <Input placeholder="例: 2026 春节营销活动" maxLength={100} />
    </Form.Item>
    <Form.Item
      name="start_time"
      label="开始时间"
      rules={[{ required: true, message: '请选择开始时间' }]}
    >
      <DatePicker style={{ width: '100%' }} />
    </Form.Item>
    <Form.Item
      name="end_time"
      label="结束时间"
      rules={[{ required: true, message: '请选择结束时间' }]}
    >
      <DatePicker style={{ width: '100%' }} />
    </Form.Item>
    <Form.Item
      name="content"
      label="具体内容"
      rules={[{ required: true, message: '请填写具体内容' }, { max: 2000 }]}
    >
      <TextArea rows={4} maxLength={2000} showCount placeholder="详细描述" />
    </Form.Item>
    <Form.Item
      name="hours"
      label="预估工时 (小时)"
      rules={[{ required: true, message: '请填写预估工时' }]}
    >
      <InputNumber min={1} max={10000} style={{ width: '100%' }} />
    </Form.Item>
    <Form.Item name="skill_tags" label="关联技能标签 (可空)">
      <Select mode="tags" placeholder="输入标签后回车" tokenSeparators={[',', '，']} />
    </Form.Item>
    <Form.Item
      name="next_approver_id"
      label="审批人 (必选)"
      rules={[{ required: true, message: '请选择审批人' }]}
    >
      <ApproverSelect />
    </Form.Item>
  </>
);

const PROFILE_EDIT_FIELDS = (
  <>
    <Form.Item
      name="field_name"
      label="字段名"
      rules={[{ required: true, message: '请填写字段名' }]}
    >
      <Input placeholder="例: job_title / mobile" />
    </Form.Item>
    <Form.Item name="old_value" label="当前值 (留空将自动从档案读取)">
      <Input placeholder="可选" />
    </Form.Item>
    <Form.Item
      name="new_value"
      label="修改为"
      rules={[{ required: true, message: '请填写修改值' }]}
    >
      <Input />
    </Form.Item>
    <Form.Item
      name="next_approver_id"
      label="审批人 (默认 admin)"
    >
      <ApproverSelect />
    </Form.Item>
  </>
);

const SKILL_TAG_EDIT_FIELDS = (
  <>
    <Form.Item
      name="tag_name"
      label="标签名"
      rules={[{ required: true, message: '请填写标签名' }]}
    >
      <Input placeholder="例: Python / 演讲" maxLength={50} />
    </Form.Item>
    <Form.Item
      name="action"
      label="操作"
      rules={[{ required: true, message: '请选择操作' }]}
    >
      <Select
        options={[
          { value: 'add', label: '新增' },
          { value: 'delete', label: '删除' },
        ]}
        placeholder="新增 / 删除"
      />
    </Form.Item>
    <Form.Item
      name="sensitivity"
      label="敏感度"
      rules={[{ required: true, message: '请选择敏感度' }]}
    >
      <Select
        options={[
          { value: 'low', label: '低 (一般技能)' },
          { value: 'medium', label: '中 (重要能力)' },
          { value: 'high', label: '高 (敏感标签)' },
        ]}
      />
    </Form.Item>
    <Form.Item name="reason" label="申请理由 (选填)">
      <TextArea rows={2} maxLength={500} />
    </Form.Item>
    <Form.Item
      name="next_approver_id"
      label="审批人 (默认 admin)"
    >
      <ApproverSelect />
    </Form.Item>
  </>
);

const TAB_FIELDS: Record<string, React.ReactNode> = {
  special_work: SPECIAL_WORK_FIELDS,
  profile_edit: PROFILE_EDIT_FIELDS,
  skill_tag_edit: SKILL_TAG_EDIT_FIELDS,
};

export interface CreateSubmissionModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: () => void;
  confirming: boolean;
  activeTab: string;
  setActiveTab: (k: any) => void;
  form: any;
}

const CreateSubmissionModal: React.FC<CreateSubmissionModalProps> = ({
  open, onCancel, onOk, confirming, activeTab, setActiveTab, form,
}) => {
  return (
    <Modal
      title="新建提交"
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      confirmLoading={confirming}
      okText="提交审批"
      cancelText="取消"
      width={720}
      destroyOnClose
    >
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k)}
        items={TAB_ITEMS}
      />
      <Form form={form} layout="vertical" preserve={false}>
        {TAB_FIELDS[activeTab]}
      </Form>
    </Modal>
  );
};

export default CreateSubmissionModal;
