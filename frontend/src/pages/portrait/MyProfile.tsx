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
  Select,
  Button,
  message,
  Spin,
  Tabs,
  Row,
  Col,
  Typography,
  Space,
  Divider,
  Table,
  Empty,
  Modal,
} from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;

const MyProfile: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<PortraitAPI.ProfileFull | null>(null);
  const [training, setTraining] = useState<PortraitAPI.TrainingRecord[]>([]);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [baseForm] = Form.useForm();
  const [politicalForm] = Form.useForm();
  const [educationForm] = Form.useForm();
  const [familyForm] = Form.useForm();
  const [contactForm] = Form.useForm();
  // P0.2: A4 兴趣 + A5 获奖 (Modal 内嵌表单)
  const [interestModalForm] = Form.useForm();
  const [awardModalForm] = Form.useForm();
  const [interestModalOpen, setInterestModalOpen] = useState(false);
  const [awardModalOpen, setAwardModalOpen] = useState(false);
  const [editingInterest, setEditingInterest] = useState<PortraitAPI.InterestInfo | null>(null);
  const [editingAward, setEditingAward] = useState<PortraitAPI.AwardInfo | null>(null);

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
        work_start_date: data.work_start_date,
        hire_date: data.hire_date,
        marital_status: data.marital_status,
      });
      politicalForm.setFieldsValue(data.political || {});
      educationForm.setFieldsValue(data.education || {});
      familyForm.setFieldsValue(data.family || {});
      contactForm.setFieldsValue(data.contact || {});
      // P0.2: 兴趣 + 获奖是 1:N 列表, 不进 setFieldsValue, 走 Table 展示
    } catch (err: any) {
      message.error(`加载档案失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchTraining = async () => {
    setTrainingLoading(true);
    try {
      const data = await PortraitAPI.getMyTraining();
      setTraining(data);
    } catch (err: any) {
      message.error(`加载培训记录失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setTrainingLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    fetchTraining();
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

  // ========================================================================
  // P0.2: A4 兴趣爱好 + A5 获奖信息 (1:N 列表, Modal 内嵌表单)
  // ========================================================================
  const openInterestModal = (rec: PortraitAPI.InterestInfo | null) => {
    setEditingInterest(rec);
    if (rec) {
      interestModalForm.setFieldsValue({
        interest_name: rec.interest_name,
        proficiency: rec.proficiency,
      });
    } else {
      interestModalForm.resetFields();
      interestModalForm.setFieldsValue({ proficiency: '入门' });
    }
    setInterestModalOpen(true);
  };

  const handleSubmitInterest = async () => {
    setSaving(true);
    try {
      const values = await interestModalForm.validateFields();
      await PortraitAPI.updateMyInterest(values);  // 后端 upsert 简化: 只保留最新一条
      message.success(editingInterest ? '兴趣已更新' : '兴趣已新增');
      setInterestModalOpen(false);
      await fetchAll();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`保存失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const openAwardModal = (rec: PortraitAPI.AwardInfo | null) => {
    setEditingAward(rec);
    if (rec) {
      awardModalForm.setFieldsValue({
        award_name: rec.award_name,
        awarding_organization: rec.awarding_organization,
        award_time: rec.award_time,
        level: rec.level,
      });
    } else {
      awardModalForm.resetFields();
    }
    setAwardModalOpen(true);
  };

  const handleSubmitAward = async () => {
    setSaving(true);
    try {
      const values = await awardModalForm.validateFields();
      // award_time 形如 YYYY-MM-DD, 已是字符串直接传
      await PortraitAPI.updateMyAward(values);
      message.success(editingAward ? '获奖已更新' : '获奖已新增');
      setAwardModalOpen(false);
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
                  <Text type="secondary">
                    注: P0.1 隐私裁剪后, 联系方式仅保留邮箱 (手机/座机/家庭电话/家庭住址/紧急联系人均不展示不编辑)
                  </Text>
                  <Form.Item label="邮箱" name="email" rules={[{ type: 'email', message: '邮箱格式不正确' }]} style={{ marginTop: 16 }}>
                    <Input placeholder="例如 name@example.com" />
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
            // P0.2: A4 兴趣爱好 (PRD §5.4) - 1:N 列表
            {
              key: 'interests',
              label: '兴趣爱好',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary">
                    记录个人兴趣与熟练度 (MVP 简化: 仅保留最新一条, 后续可扩展为多选列表)
                  </Text>
                  {(profile?.interests?.length ?? 0) === 0 ? (
                    <Empty description="暂无兴趣爱好" />
                  ) : (
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={profile!.interests || []}
                      pagination={false}
                      columns={[
                        { title: '兴趣', dataIndex: 'interest_name', width: 200 },
                        { title: '熟练度', dataIndex: 'proficiency', width: 120 },
                        {
                          title: '更新时间',
                          dataIndex: 'updated_at',
                          render: (v: string) => v?.slice(0, 19).replace('T', ' ') || '—',
                        },
                        {
                          title: '操作',
                          width: 100,
                          render: (_: any, rec: PortraitAPI.InterestInfo) => (
                            <Button size="small" onClick={() => openInterestModal(rec)}>
                              编辑
                            </Button>
                          ),
                        },
                      ]}
                    />
                  )}
                  <Button type="primary" onClick={() => openInterestModal(null)} loading={saving}>
                    新增兴趣
                  </Button>
                </Space>
              ),
            },
            // P0.2: A5 获奖信息 (PRD §5.5) - 1:N 列表
            {
              key: 'awards',
              label: '获奖信息',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary">
                    记录个人获奖情况 (MVP 简化: 仅保留最新一条, 后续可扩展为多选列表)
                  </Text>
                  {(profile?.awards?.length ?? 0) === 0 ? (
                    <Empty description="暂无获奖记录" />
                  ) : (
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={profile!.awards || []}
                      pagination={false}
                      columns={[
                        { title: '奖项名称', dataIndex: 'award_name', width: 240 },
                        { title: '颁奖机构', dataIndex: 'awarding_organization', width: 200 },
                        { title: '级别', dataIndex: 'level', width: 100 },
                        {
                          title: '获奖时间',
                          dataIndex: 'award_time',
                          width: 120,
                          render: (v: string | null) => v || '—',
                        },
                        {
                          title: '操作',
                          width: 100,
                          render: (_: any, rec: PortraitAPI.AwardInfo) => (
                            <Button size="small" onClick={() => openAwardModal(rec)}>
                              编辑
                            </Button>
                          ),
                        },
                      ]}
                    />
                  )}
                  <Button type="primary" onClick={() => openAwardModal(null)} loading={saving}>
                    新增获奖
                  </Button>
                </Space>
              ),
            },
            {
              key: 'training',
              label: '培训记录',
              children: (
                <Spin spinning={trainingLoading}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text type="secondary">
                      个人培训历史 (PRD §10.3 D2 占位, 按培训时间倒序)
                    </Text>
                    {training.length === 0 ? (
                      <Empty description="暂无培训记录" />
                    ) : (
                      <Table
                        rowKey="id"
                        size="small"
                        dataSource={training}
                        pagination={{ pageSize: 10 }}
                        columns={[
                          {
                            title: '培训时间',
                            dataIndex: 'training_at',
                            width: 180,
                            render: (v: string) => v?.slice(0, 19).replace('T', ' '),
                          },
                          { title: '培训名', dataIndex: 'training_name', width: 200 },
                          { title: '类型', dataIndex: 'training_type', width: 100 },
                          { title: '培训机构', dataIndex: 'institution' },
                          { title: '证书编号', dataIndex: 'certificate_no', width: 120 },
                          {
                            title: '有效期',
                            dataIndex: 'valid_until',
                            width: 110,
                            render: (v: string | null) => v || '—',
                          },
                        ]}
                      />
                    )}
                  </Space>
                </Spin>
              ),
            },
          ]}
        />

        {/* P0.2: A4 兴趣爱好 Modal */}
        <Modal
          title={editingInterest ? '编辑兴趣' : '新增兴趣'}
          open={interestModalOpen}
          onCancel={() => setInterestModalOpen(false)}
          onOk={handleSubmitInterest}
          confirmLoading={saving}
          destroyOnClose
        >
          <Form form={interestModalForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item
              label="兴趣名"
              name="interest_name"
              rules={[{ required: true, message: '请输入兴趣名' }]}
            >
              <Input placeholder="例如 摄影 / 篮球 / 钢琴" maxLength={100} />
            </Form.Item>
            <Form.Item
              label="熟练度"
              name="proficiency"
              rules={[{ required: true, message: '请选择熟练度' }]}
            >
              <Select
                options={[
                  { value: '入门', label: '入门' },
                  { value: '熟练', label: '熟练' },
                  { value: '精通', label: '精通' },
                ]}
              />
            </Form.Item>
          </Form>
        </Modal>

        {/* P0.2: A5 获奖信息 Modal */}
        <Modal
          title={editingAward ? '编辑获奖' : '新增获奖'}
          open={awardModalOpen}
          onCancel={() => setAwardModalOpen(false)}
          onOk={handleSubmitAward}
          confirmLoading={saving}
          destroyOnClose
        >
          <Form form={awardModalForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item
              label="奖项名称"
              name="award_name"
              rules={[{ required: true, message: '请输入奖项名称' }]}
            >
              <Input placeholder="例如 优秀员工 / 业务标兵" maxLength={200} />
            </Form.Item>
            <Form.Item label="颁奖机构" name="awarding_organization">
              <Input placeholder="例如 中国人民银行 / 总行" maxLength={200} />
            </Form.Item>
            <Form.Item label="获奖时间" name="award_time">
              <Input placeholder="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item label="级别" name="level">
              <Select
                allowClear
                options={[
                  { value: '国家级', label: '国家级' },
                  { value: '省部级', label: '省部级' },
                  { value: '行级', label: '行级' },
                ]}
              />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
};

export default MyProfile;