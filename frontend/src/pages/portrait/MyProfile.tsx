/**
 * 数字画像-我的档案 (P5 阶段, 批次 9)
 *
 * PRD §A1-A5: 我的档案 + 9 子表 (P5 MVP 仅展示 5 个核心子表: 政治面貌/学历/家属/联系方式/基本信息)
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有更新走 api (axios + Bearer)
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Spin,
  Tabs,
  Row,
  Col,
  Typography,
  Space,
  Divider,
} from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;

const MyProfile: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<PortraitAPI.ProfileFull | null>(null);
  const [baseForm] = Form.useForm();
  const [politicalForm] = Form.useForm();
  const [educationForm] = Form.useForm();
  const [familyForm] = Form.useForm();
  const [contactForm] = Form.useForm();

  const fetchAll = async () => {
    setLoading(true);
    try {
      const data = await PortraitAPI.getMyProfile();
      setProfile(data);
      baseForm.setFieldsValue({
        gender: data.gender,
        nation: data.nation,
        birth_date: data.birth_date,
        job_title: data.job_title,
        native_place: data.native_place,
        birth_place: data.birth_place,
        household_place: data.household_place,
        work_start_date: data.work_start_date,
        hire_date: data.hire_date,
        marital_status: data.marital_status,
      });
      politicalForm.setFieldsValue(data.political || {});
      educationForm.setFieldsValue(data.education || {});
      familyForm.setFieldsValue(data.family || {});
      contactForm.setFieldsValue(data.contact || {});
    } catch (err: any) {
      message.error(`加载档案失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSaveBase = async () => {
    setSaving(true);
    try {
      const values = await baseForm.validateFields();
      await PortraitAPI.updateMyProfile(values);
      message.success('基本信息已保存');
      await fetchAll();
    } catch (err: any) {
      if (err?.errorFields) return;  // 表单校验失败
      message.error(`保存失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSub = async (
    form: any,
    api: (data: any) => Promise<any>
  ) => {
    setSaving(true);
    try {
      const values = await form.validateFields();
      await api(values);
      message.success('已保存');
      await fetchAll();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`保存失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading && !profile) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <BreadcrumbNav items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '我的档案' }]} />
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>我的档案</Title>
            {profile && (
              <Text type="secondary">
                {profile.user_name} | EHR {profile.ehr_id} | {profile.department}
              </Text>
            )}
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchAll} loading={loading}>
            刷新
          </Button>
        }
      >
        <Tabs
          items={[
            {
              key: 'base',
              label: '基本信息',
              children: (
                <Form form={baseForm} layout="vertical" style={{ maxWidth: 720 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item label="性别" name="gender">
                        <Input placeholder="例如 male / female" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="民族" name="nation">
                        <Input placeholder="例如 汉族" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="出生日期" name="birth_date">
                        <Input placeholder="YYYY-MM-DD" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="职务" name="job_title">
                        <Input placeholder="例如 主任 / 副主任" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="籍贯" name="native_place">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="出生地" name="birth_place">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="户籍地" name="household_place">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="参加工作日期" name="work_start_date">
                        <Input placeholder="YYYY-MM-DD" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="入职本院日期" name="hire_date">
                        <Input placeholder="YYYY-MM-DD" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="婚姻状况" name="marital_status">
                        <Input placeholder="未婚 / 已婚 / 离异" />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Divider />
                  <Text type="secondary">
                    注: 证件类型/证件号/是否应急人员 属受保护字段, 修改需走 profile_edit 审批流 (P5 MVP 暂未提供前端表单)
                  </Text>
                  <Form.Item style={{ marginTop: 16 }}>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      onClick={handleSaveBase}
                      loading={saving}
                    >
                      保存基本信息
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'political',
              label: '政治面貌',
              children: (
                <Form form={politicalForm} layout="vertical" style={{ maxWidth: 720 }}>
                  <Form.Item label="政治面貌" name="political_status">
                    <Input placeholder="群众 / 共青团员 / 中共党员" />
                  </Form.Item>
                  <Form.Item label="加入日期" name="join_date">
                    <Input placeholder="YYYY-MM-DD" />
                  </Form.Item>
                  <Form.Item label="介绍人" name="introducer">
                    <Input />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() =>
                        handleSaveSub(politicalForm, PortraitAPI.updateMyPolitical)
                      }
                    >
                      保存
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'education',
              label: '学历',
              children: (
                <Form form={educationForm} layout="vertical" style={{ maxWidth: 720 }}>
                  <Form.Item label="学历类别" name="education_category">
                    <Input placeholder="全日制 / 在职" />
                  </Form.Item>
                  <Form.Item label="学历类型" name="education_type">
                    <Input placeholder="普通高等教育 / 成人教育" />
                  </Form.Item>
                  <Form.Item label="学历层次" name="education_level">
                    <Input placeholder="本科 / 硕士 / 博士" />
                  </Form.Item>
                  <Form.Item label="学位" name="degree">
                    <Input placeholder="学士 / 硕士 / 博士" />
                  </Form.Item>
                  <Form.Item label="毕业院校" name="school">
                    <Input />
                  </Form.Item>
                  <Form.Item label="专业" name="major_name">
                    <Input />
                  </Form.Item>
                  <Form.Item label="学制年限" name="duration_years">
                    <Input placeholder="例如 3 年 / 4 年" />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() =>
                        handleSaveSub(educationForm, PortraitAPI.updateMyEducation)
                      }
                    >
                      保存
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'family',
              label: '家属',
              children: (
                <Form form={familyForm} layout="vertical" style={{ maxWidth: 720 }}>
                  <Form.Item label="成员姓名" name="member_name">
                    <Input />
                  </Form.Item>
                  <Form.Item label="关系" name="relationship">
                    <Input placeholder="配偶 / 子女 / 父母" />
                  </Form.Item>
                  <Form.Item label="出生日期" name="birth_date">
                    <Input placeholder="YYYY-MM-DD" />
                  </Form.Item>
                  <Form.Item label="政治面貌" name="political_status">
                    <Input />
                  </Form.Item>
                  <Form.Item label="工作单位" name="work_unit">
                    <Input />
                  </Form.Item>
                  <Form.Item label="职务" name="job_title">
                    <Input />
                  </Form.Item>
                  <Form.Item label="联系电话" name="contact_phone">
                    <Input />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() =>
                        handleSaveSub(familyForm, PortraitAPI.updateMyFamily)
                      }
                    >
                      保存
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'contact',
              label: '联系方式',
              children: (
                <Form form={contactForm} layout="vertical" style={{ maxWidth: 720 }}>
                  <Form.Item label="手机号" name="mobile" rules={[{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]}>
                    <Input placeholder="11 位手机号" />
                  </Form.Item>
                  <Form.Item label="邮箱" name="email" rules={[{ type: 'email', message: '邮箱格式不正确' }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item label="现住址" name="address">
                    <Input />
                  </Form.Item>
                  <Form.Item label="紧急联系人" name="emergency_contact">
                    <Input />
                  </Form.Item>
                  <Form.Item label="紧急联系人电话" name="emergency_phone">
                    <Input />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() =>
                        handleSaveSub(contactForm, PortraitAPI.updateMyContact)
                      }
                    >
                      保存
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default MyProfile;