/**
 * P7 创建提交 Modal (B1 专项工作 + B2 活动报名 + A2 档案修改 + A3 亮点标签 四合一)
 *
 * Week 2 P0.5: 加 B2 活动报名 (activity_claim)
 * 集成指南 §5 雷区 7: 不绕过 Depends
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
  Switch,
  message,
} from 'antd';
import * as PortraitAPI from '../../api/portrait';

const { TextArea } = Input;

const TAB_ITEMS = [
  { key: 'special_work', label: '专项工作 (B1)' },
  { key: 'activity_claim', label: '活动报名 (B2)' },
  { key: 'profile_edit', label: '档案修改 (A2)' },
];

// 审批人下拉
// 数据源: GET /users/members (员工通讯录最小集, 任意登录用户可访问)
// 不能用 /users/: 那个端点需要 user:view 权限, 普通员工拿不到 → 下拉恒空 →
// next_approver_id 必填 → B1/B2 整个提交不了。参见 api/users.ts 的接口注释。
const ApproverSelect: React.FC<{ value?: number; onChange?: (v: number) => void; disabled?: boolean }> = ({ value, onChange, disabled }) => {
  const [users, setUsers] = React.useState<{ id: number; name: string; ehr_id: string }[]>([]);
  React.useEffect(() => {
    (async () => {
      try {
        const { getUserMembers } = await import('../../api/users');
        const members = await getUserMembers({ limit: 1000 });
        setUsers(
          (members || []).map((u) => ({
            id: u.id,
            name: u.name || u.username || `#${u.id}`,
            ehr_id: u.ehr_id || '-',
          })),
        );
      } catch (err: any) {
        // Rule 12: 失败必须显性化。之前这里是 catch {} 静默吞掉, 导致下拉恒为空
        // 却无任何提示, B1/B2 对普通员工整体不可用且难以定位。
        message.error(`审批人列表加载失败: ${err?.response?.data?.detail || err.message}`);
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

// B2 活动报名 (PRD §6.2) — 复用 submission (activity_claim type), 跟 B1 同构
// 字段: 活动名/活动时间/活动类型/主办方/报名原因/可参加排练
const ACTIVITY_CLAIM_FIELDS = (
  <>
    <Form.Item
      name="activity_name"
      label="活动名"
      rules={[{ required: true, message: '请填写活动名' }, { max: 200 }]}
    >
      <Input placeholder="例: 2026 春节文艺汇演 / 总行运动会" maxLength={200} />
    </Form.Item>
    <Form.Item
      name="activity_type"
      label="活动类型"
      rules={[{ required: true, message: '请选择活动类型' }]}
    >
      <Select
        options={[
          { value: '运动会', label: '运动会' },
          { value: '文艺', label: '文艺' },
          { value: '志愿', label: '志愿' },
          { value: '培训', label: '培训' },
          { value: '其他', label: '其他' },
        ]}
        placeholder="选择活动类型"
      />
    </Form.Item>
    <Form.Item
      name="activity_time"
      label="活动时间"
      rules={[{ required: true, message: '请选择活动时间' }]}
    >
      <DatePicker style={{ width: '100%' }} />
    </Form.Item>
    <Form.Item
      name="organizer"
      label="主办方"
      rules={[{ required: true, message: '请填写主办方' }, { max: 200 }]}
    >
      <Input placeholder="例: 总行工会 / 中国金融体育协会" maxLength={200} />
    </Form.Item>
    <Form.Item
      name="reason"
      label="报名原因"
      rules={[{ required: true, message: '请填写报名原因' }, { max: 1000 }]}
    >
      <TextArea rows={3} maxLength={1000} showCount placeholder="为什么想参加" />
    </Form.Item>
    <Form.Item
      name="can_rehearse"
      label="是否可参加排练"
      valuePropName="checked"
      initialValue={true}
    >
      <Switch checkedChildren="可" unCheckedChildren="否" />
    </Form.Item>
    <Form.Item
      name="next_approver_id"
      label="审批人 (本组组长 / 管理员)"
      rules={[{ required: true, message: '请选择审批人' }]}
    >
      <ApproverSelect />
    </Form.Item>
  </>
);

const TAB_FIELDS: Record<string, React.ReactNode> = {
  special_work: SPECIAL_WORK_FIELDS,
  activity_claim: ACTIVITY_CLAIM_FIELDS,
  profile_edit: PROFILE_EDIT_FIELDS,
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
