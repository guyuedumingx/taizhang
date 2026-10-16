/**
 * A11 应急先锋队卡片 (Week 3 P0.4)
 *
 * 业务: "这个员工是不是应急先锋队成员" — 纯标识, 不涉及隐私字段
 *
 * 权限: 仅 admin 可改 (用户 2026-10-10 决策, 覆盖 PRD 原"走审批"的说法)
 *   - admin: 看 Switch 可点击
 *   - 员工/组长: 只读展示, 无 Switch
 *
 * 集成指南 §5 雷区 7: 走 api, 不绕过 Depends
 * 集成指南 §5 雷区 12: 失败显性化, 改失败 message.error
 */
import React, { useState } from 'react';
import {
  Card,
  Tag,
  Switch,
  Space,
  Modal,
  Input,
  Form,
  message,
  Typography,
  Alert,
} from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import { useAuthStore } from '../../stores/authStore';

const { Text, Paragraph } = Typography;

interface EmergencyStaffCardProps {
  /** 当前用户 id (admin 操作目标 = 本人档案, 因本卡片挂在"我的档案"页) */
  currentUserId: number;
  /** 当前值 */
  isEmergencyStaff: boolean;
  /** 变更后刷新父组件 */
  onChanged: () => Promise<void> | void;
}

const EmergencyStaffCard: React.FC<EmergencyStaffCardProps> = ({
  currentUserId,
  isEmergencyStaff,
  onChanged,
}) => {
  const [saving, setSaving] = useState(false);
  const [reasonModalOpen, setReasonModalOpen] = useState(false);
  const [pendingValue, setPendingValue] = useState(false);
  const [form] = Form.useForm();

  // 权限: 仅 admin 可改 (与 DrillsPage / EntryExitPage 同一惯例, Rule 11)
  const isAdmin = useAuthStore.getState().user?.roles?.includes('admin') ?? false;

  const handleToggle = (checked: boolean) => {
    setPendingValue(checked);
    form.setFieldValue('reason', '');
    setReasonModalOpen(true);
  };

  const handleConfirm = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await PortraitAPI.setEmergencyStaff(currentUserId, {
        is_emergency_staff: pendingValue,
        reason: values.reason,
      });
      message.success(pendingValue ? '已设为应急先锋队成员' : '已取消应急先锋队资格');
      setReasonModalOpen(false);
      await onChanged();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`操作失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setReasonModalOpen(false);
    setPendingValue(isEmergencyStaff);
  };

  return (
    <>
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: isEmergencyStaff ? '#faad14' : '#999' }} />
            <span>应急先锋队</span>
          </Space>
        }
        size="small"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space>
            <Text strong>当前状态:</Text>
            {isEmergencyStaff ? (
              <Tag icon={<SafetyCertificateOutlined />} color="gold">
                应急先锋队成员
              </Tag>
            ) : (
              <Tag>非应急先锋队</Tag>
            )}
            {isAdmin && (
              <Switch
                checked={isEmergencyStaff}
                checkedChildren="是"
                unCheckedChildren="否"
                loading={saving}
                onChange={handleToggle}
              />
            )}
          </Space>

          <Alert
            type="info"
            showIcon
            message={
              isAdmin
                ? '该标识代表组织认定 (非个人意愿), 仅管理员可修改, 每次修改会记录操作日志。'
                : '该标识由管理员认定, 如需变更请联系管理员。'
            }
          />

          <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
            说明: 消防演练参与记录请查看"演练台账"页面, 与本标识相互独立。
          </Paragraph>
        </Space>
      </Card>

      <Modal
        title={pendingValue ? '设为应急先锋队成员' : '取消应急先锋队资格'}
        open={reasonModalOpen}
        onCancel={handleCancel}
        onOk={handleConfirm}
        confirmLoading={saving}
        okText="确认"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="reason"
            label="变更原因 (写入操作日志)"
            rules={[{ max: 200, message: '原因不超过 200 字' }]}
          >
            <Input.TextArea
              rows={3}
              maxLength={200}
              showCount
              placeholder="例: 2026 年应急先锋队名单 / 已调离应急部门"
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default EmergencyStaffCard;
