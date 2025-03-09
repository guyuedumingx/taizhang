import React from 'react';
import { Form, Input, Select, DatePicker, Button, Row, Col, Card } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { LogQueryParams } from '../../types';

const { Option } = Select;
const { RangePicker } = DatePicker;

// 扩展LogQueryParams类型，添加日期选择器需要的字段
interface FormValues extends LogQueryParams {
  date_range?: any;
}

interface LogSearchFormProps {
  type: 'system' | 'audit';
  onSearch: (values: FormValues) => void;
  onReset: () => void;
  loading: boolean;
}

const LogSearchForm: React.FC<LogSearchFormProps> = ({
  type,
  onSearch,
  onReset,
  loading,
}) => {
  const [form] = Form.useForm();

  const handleReset = () => {
    form.resetFields();
    onReset();
  };

  return (
    <Card style={{ marginBottom: 16 }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={onSearch}
        initialValues={{}}
      >
        <Row gutter={16}>
          {type === 'system' && (
            <>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="level" label="日志级别">
                  <Select placeholder="选择日志级别" allowClear>
                    <Option value="debug">调试</Option>
                    <Option value="info">信息</Option>
                    <Option value="warning">警告</Option>
                    <Option value="error">错误</Option>
                    <Option value="critical">严重</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="module" label="模块">
                  <Input placeholder="输入模块名称" />
                </Form.Item>
              </Col>
            </>
          )}

          {type === 'audit' && (
            <>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="action" label="操作类型">
                  <Select placeholder="选择操作类型" allowClear>
                    <Option value="create">创建</Option>
                    <Option value="update">更新</Option>
                    <Option value="delete">删除</Option>
                    <Option value="view">查看</Option>
                    <Option value="login">登录</Option>
                    <Option value="logout">登出</Option>
                    <Option value="submit">提交</Option>
                    <Option value="approve">批准</Option>
                    <Option value="reject">拒绝</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="ledger_id" label="台账ID">
                  <Input placeholder="输入台账ID" />
                </Form.Item>
              </Col>
            </>
          )}

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="user_id" label="用户ID">
              <Input placeholder="输入用户ID" />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="ip_address" label="IP地址">
              <Input placeholder="输入IP地址" />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="date_range" label="时间范围">
              <RangePicker
                style={{ width: '100%' }}
                showTime
                format="YYYY-MM-DD HH:mm:ss"
              />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="keyword" label="关键词">
              <Input placeholder="输入关键词搜索" />
            </Form.Item>
          </Col>

          <Col xs={24} style={{ textAlign: 'right', marginTop: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SearchOutlined />}
              loading={loading}
              style={{ marginRight: 8 }}
            >
              搜索
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Col>
        </Row>
      </Form>
    </Card>
  );
};

export default LogSearchForm; 