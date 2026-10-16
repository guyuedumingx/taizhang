/**
 * 1:N 子表通用卡片 (Week 2 P0.5 - A1 12 卡片)
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有更新走 api
 * 集成指南 §5 雷区 12: 失败显性化, message.error
 *
 * 5 张子表 (简历/奖惩/资格/成果/语言) 全部使用此组件:
 *  - 表格展示现有条目
 *  - 新增按钮 → 弹 Modal 内嵌表单
 *  - 表格行尾: 编辑/删除按钮
 */
import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  DatePicker,
  Select,
  Space,
  Popconfirm,
  message,
  Empty,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';

// 字段定义 (驱动 Modal 表单)
export type SubTableField =
  | { name: string; label: string; type: 'text'; required?: boolean }
  | { name: string; label: string; type: 'date'; required?: boolean }
  | {
      name: string;
      label: string;
      type: 'select';
      required?: boolean;
      options: Array<{ value: string; label: string }>;
    };

export interface SubTableCardProps<T extends { id?: number }> {
  title: string;
  dataSource: T[];
  columns: Array<{
    title: string;
    dataIndex: string;
    width?: number;
    ellipsis?: boolean;
    render?: (v: any, rec: T) => React.ReactNode;
  }>;
  addFields: SubTableField[];
  onAdd: (data: any) => Promise<any>;
  onUpdate: (id: number, data: any) => Promise<any>;
  onDelete: (id: number) => Promise<any>;
  onChanged: () => Promise<void> | void;
}

function SubTableCard<T extends { id?: number }>({
  title,
  dataSource,
  columns,
  addFields,
  onAdd,
  onUpdate,
  onDelete,
  onChanged,
}: SubTableCardProps<T>) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const openAdd = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (rec: T) => {
    setEditing(rec);
    // 转换日期字符串 → dayjs
    const values: any = { ...rec };
    for (const f of addFields) {
      if (f.type === 'date' && values[f.name]) {
        values[f.name] = dayjs(values[f.name] as string);
      }
    }
    form.setFieldsValue(values);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // 转换 dayjs → YYYY-MM-DD
      const payload: any = { ...values };
      for (const f of addFields) {
        if (f.type === 'date' && payload[f.name]) {
          payload[f.name] = (payload[f.name] as Dayjs).format('YYYY-MM-DD');
        }
      }
      setSaving(true);
      if (editing && editing.id) {
        await onUpdate(editing.id, payload);
        message.success('已更新');
      } else {
        await onAdd(payload);
        message.success('已新增');
      }
      setModalOpen(false);
      await onChanged();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`保存失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await onDelete(id);
      message.success('已删除');
      await onChanged();
    } catch (err: any) {
      message.error(`删除失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  return (
    <Card
      title={title}
      size="small"
      extra={
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={openAdd}
        >
          新增
        </Button>
      }
    >
      {dataSource.length === 0 ? (
        <Empty description="暂无条目, 点击右上角'新增'" />
      ) : (
        <Table
          rowKey="id"
          size="small"
          dataSource={dataSource}
          pagination={false}
          columns={[
            ...columns,
            {
              title: '操作',
              width: 120,
              render: (_: any, rec: T) => (
                <Space>
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(rec)}
                  >
                    编辑
                  </Button>
                  <Popconfirm
                    title="确认删除?"
                    onConfirm={() => rec.id && handleDelete(rec.id)}
                  >
                    <Button
                      type="link"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      )}

      <Modal
        title={editing ? '编辑' : '新增'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {addFields.map((f) => (
            <Form.Item
              key={f.name}
              name={f.name}
              label={f.label}
              rules={
                f.required
                  ? [{ required: true, message: `请输入${f.label}` }]
                  : []
              }
            >
              {f.type === 'text' && <Input maxLength={500} />}
              {f.type === 'date' && (
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              )}
              {f.type === 'select' && (
                <Select options={f.options} allowClear />
              )}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </Card>
  );
}

export default SubTableCard;
