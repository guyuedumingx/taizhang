/**
 * 新建家访两步表单 (C1 PRD §7.1)
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 走 api
 * 集成指南 §5 雷区 12: 失败显性化, message.error
 *
 * Step 1 - 家访明细: 被访人/年度/时间/方式/地址/双人员/是否已访/扫描件
 *   - 选被访人 → onChange 调 getProfileByEhr → 自动回填 position
 *   - 扫描件 Upload: beforeUpload 校验类型 + ≤5MB, customRequest 同步调 uploadHomeVisitScanFile
 *   - 第二家访人 Select: 同组成员
 * Step 2 - 家访记录表: 团队名称(固定"审核处理团队") + 岗位 + 家访日期 + 反馈(支持"预填七点模板")
 *   - Week 3 隐私裁剪: 删除家庭地址/手机/家庭电话/家属1/家属2 12 个字段
 */
import React, { useEffect, useState } from 'react';
import {
  Modal,
  Steps,
  Form,
  Select,
  Input,
  Switch,
  DatePicker,
  Upload,
  Button,
  Space,
  message,
  Spin,
  Row,
  Col,
  Tooltip,
  Radio,
} from 'antd';
import { InboxOutlined, ThunderboltOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import * as PortraitAPI from '../../api/portrait';
import { SEVEN_POINT_TEMPLATE } from './constants/sevenPointTemplate';

const { Dragger } = Upload;
const { TextArea } = Input;

interface CreateHomeVisitModalProps {
  open: boolean;
  onCancel: () => void;
  onSuccess: (record: PortraitAPI.HomeVisitDetail) => void;
  /** 列出"可选被访人" — 同组组员 (含 leader 自己, leader 通常不需要自己访自己) */
  visitedCandidates: Array<{ ehr_id: string; name: string }>;
  /** 列出"可选第二家访人" — 同组组员 (排除自己) */
  coVisitorCandidates: Array<{ id: number; name: string; ehr_id: string }>;
  /** 当前登录用户 id, 用于排除在"第二家访人"选项外 */
  currentUserId: number;
  /** 当前登录用户的 ehr_id, 排除在"被家访人"选项外 (不能自己访自己) */
  currentUserEhrId: string;
  /** 'create' = 新建草稿 (默认), 'edit' = 编辑已有草稿 (Week 3 P0.3) */
  mode?: 'create' | 'edit';
  /** 编辑模式下, 待编辑的草稿数据 (用于 setFieldsValue 回填) */
  initialValues?: PortraitAPI.HomeVisitDetail;
  /** 编辑模式下, 草稿 id (调 updateHomeVisit 用) */
  visitId?: number;
}

interface UploadedScan {
  file_path: string;
  file_url: string;
  file_name: string;
  file_size: number;
}

const MAX_SCAN_SIZE = 5 * 1024 * 1024;
const ALLOWED_SCAN_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];

const CreateHomeVisitModal: React.FC<CreateHomeVisitModalProps> = ({
  open,
  onCancel,
  onSuccess,
  visitedCandidates,
  coVisitorCandidates,
  currentUserId,
  currentUserEhrId,
  mode = 'create',
  initialValues,
  visitId,
}) => {
  const [form] = Form.useForm();
  const [step, setStep] = useState(0);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadedScan, setUploadedScan] = useState<UploadedScan | null>(null);
  const [previewTemplateOpen, setPreviewTemplateOpen] = useState(false);

  // 进入时重置表单
  useEffect(() => {
    if (open) {
      form.resetFields();
      // Step 2 团队名称固定值 (Rule 12: 即使前端 disabled 绕过, 后端兜底校验)
      form.setFieldValue('team_name', '审核处理团队');
      // 新建时默认"未提交" —— 不是让用户凭空选, 而是给一个明确的起点;
      // 仍是必填, 上传了文件用户仍要显式改成"已提交"。
      form.setFieldValue('scan_status', '未提交');
      setStep(0);
      setUploadedScan(null);

      // Week 3 P0.3: 编辑模式回填字段 (仅非隐私字段, 隐私字段已从表单删除)
      if (mode === 'edit' && initialValues) {
        form.setFieldsValue({
          visited_ehr_id: initialValues.visited_ehr_id,
          visit_year: initialValues.visit_year,
          visit_time: initialValues.visit_time
            ? (dayjs as any)(initialValues.visit_time)
            : null,
          visit_method: initialValues.visit_method,
          visit_address: initialValues.visit_address,
          co_visitor_user_id: initialValues.co_visitor_user_id,
          is_visited: initialValues.is_visited,
          visit_date: initialValues.visit_date
            ? (dayjs as any)(initialValues.visit_date)
            : null,
          position: initialValues.position,
          contact_phone: initialValues.contact_phone,
          feedback: initialValues.feedback,
          scan_status: initialValues.scan_status || '未提交',
        });
        // 已有扫描件回显
        if (initialValues.scan_file_path) {
          setUploadedScan({
            file_path: initialValues.scan_file_path,
            file_url: initialValues.scan_file_url || '',
            file_name: initialValues.scan_file_path.split('/').pop() || '',
            file_size: 0,
          });
        }
      }
    }
  }, [open, mode, initialValues, form]);

  // 选被访人 → 自动回填档案
  const handleVisitedChange = async (ehrId: string) => {
    if (!ehrId) {
      return;
    }
    setLoadingProfile(true);
    try {
      const profile = await PortraitAPI.getProfileByEhr(ehrId);
      // 回填 Step 2 字段 (Week 3 隐私裁剪: 只回填岗位)
      form.setFieldsValue({
        position: profile.job_title || '',
      });
      message.success(`已自动回填 ${profile.user_name || ehrId} 的岗位`);
    } catch (err: any) {
      // 档案不存在不阻塞, 仅提示
      message.warning(`未找到 ${ehrId} 的档案, 请手动填写`);
    } finally {
      setLoadingProfile(false);
    }
  };

  // 扫描件上传 (beforeUpload 校验, customRequest 同步调后端)
  const handleScanUpload = (file: File): boolean => {
    if (!ALLOWED_SCAN_TYPES.includes(file.type)) {
      message.error('扫描件仅支持 PDF / JPG / PNG');
      return false;
    }
    if (file.size > MAX_SCAN_SIZE) {
      message.error(`扫描件大小 ${(file.size / 1024 / 1024).toFixed(2)}MB 超过 5MB 上限`);
      return false;
    }
    // 校验通过后, 异步上传
    void (async () => {
      setUploading(true);
      try {
        const res = await PortraitAPI.uploadHomeVisitScanFile(file);
        setUploadedScan({
          file_path: res.file_path,
          file_url: res.file_url,
          file_name: res.original_name,
          file_size: res.file_size,
        });
        form.setFieldValue('scan_file_path', res.file_path);
        message.success(`已上传 ${res.original_name}`);
      } catch (err: any) {
        message.error(`上传失败: ${err?.response?.data?.detail || err.message}`);
      } finally {
        setUploading(false);
      }
    })();
    return false;  // 阻止 antd 默认上传行为
  };

  const handleRemoveScan = () => {
    setUploadedScan(null);
    form.setFieldValue('scan_file_path', undefined);
  };

  // 预填七点模板
  const handleFillTemplate = () => {
    const current = form.getFieldValue('feedback') || '';
    if (current.trim()) {
      Modal.confirm({
        title: '已填写反馈, 是否覆盖?',
        onOk: () => form.setFieldValue('feedback', SEVEN_POINT_TEMPLATE),
      });
    } else {
      form.setFieldValue('feedback', SEVEN_POINT_TEMPLATE);
      message.success('已预填七点反馈模板');
    }
  };

  // Step 1 → Step 2 校验
  const handleNext = async () => {
    try {
      await form.validateFields([
        'visited_ehr_id',
        'visit_year',
        'visit_time',
        'visit_method',
      ]);
      setStep(1);
    } catch {
      // antd 已显示字段错误
    }
  };

  // 提交
  const handleSubmit = async () => {
    try {
      const allValues = await form.validateFields();
      setSubmitting(true);
      const payload: PortraitAPI.HomeVisitCreatePayload = {
        visited_ehr_id: allValues.visited_ehr_id,
        visit_year: allValues.visit_year,
        visit_time: (allValues.visit_time as Dayjs).format('YYYY-MM-DDTHH:mm:ss'),
        visit_method: allValues.visit_method,
        visit_address: allValues.visit_address,
        is_visited: allValues.is_visited ?? false,
        visit_date: allValues.visit_date
          ? (allValues.visit_date as Dayjs).format('YYYY-MM-DD')
          : undefined,
        // visitor_info 由后端拼装 (PRD B.4 第 10 列 1.<姓名>，<岗位>)。
        // 前端此前提交 allValues.visitor_info, 但表单里没有该表单项 → 恒 undefined。
        position: allValues.position,
        // 联系电话由组长手填: Profile/ContactInfo 经 P0.1 隐私裁剪后已无电话字段,
        // PRD §7.1 要求的"从档案自动回填"无数据源 (2026-10-14 用户决定: 手工填)。
        contact_phone: allValues.contact_phone,
        feedback: allValues.feedback,
        co_visitor_user_id: allValues.co_visitor_user_id || null,
        scan_file_path: uploadedScan?.file_path || null,
        // PRD 附录 B.4 第 14 列, 必填状态值。上传了文件不代表业务上这张记录表
        // 已提交 —— 这两件事分开记, 以前只有一个 scan_file_path 表达不了后者。
        scan_status: allValues.scan_status || '未提交',
        team_name: '审核处理团队',  // 固定值, 后端兜底校验
      };
      // Week 3 P0.3: 编辑模式调 update, 否则 create
      let record: PortraitAPI.HomeVisitDetail;
      if (mode === 'edit' && visitId) {
        record = await PortraitAPI.updateHomeVisit(visitId, payload);
      } else {
        record = await PortraitAPI.createHomeVisit(payload);
      }
      // 成功提示由父组件 (HomeVisits) 统一发出, 此处不再重复弹窗
      onSuccess(record);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(
        `${mode === 'edit' ? '更新' : '创建'}失败: ${err?.response?.data?.detail || err.message}`
      );
    } finally {
      setSubmitting(false);
    }
  };

  // 年份下拉: 近 10 年
  const yearOptions = Array.from({ length: 10 }, (_, i) => {
    const y = new Date().getFullYear() - i;
    return { label: `${y} 年`, value: y };
  });

  return (
    <>
      <Modal
        title={mode === 'edit' ? '编辑家访草稿' : '新建家访'}
        open={open}
        onCancel={onCancel}
        width={900}
        destroyOnClose
        footer={null}
        maskClosable={false}
      >
        <Steps
          current={step}
          items={[
            { title: '家访明细' },
            { title: '家访记录表' },
          ]}
          style={{ marginBottom: 24 }}
        />

        <Spin spinning={loadingProfile || uploading}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              visit_method: '线下',
              is_visited: true,
              visit_year: new Date().getFullYear(),
              team_name: '审核处理团队',
            }}
          >
            {step === 0 && (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="visited_ehr_id"
                      label="被家访人"
                      rules={[{ required: true, message: '请选择被家访人' }]}
                    >
                      <Select
                        showSearch
                        placeholder="选择本组成员"
                        optionFilterProp="label"
                        onChange={handleVisitedChange}
                        options={visitedCandidates
                          .filter((c) => c.ehr_id !== currentUserEhrId)
                          .map((c) => ({ label: `${c.name} (${c.ehr_id})`, value: c.ehr_id }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item
                      name="visit_year"
                      label="年度"
                      rules={[{ required: true, message: '请选择年度' }]}
                    >
                      <Select options={yearOptions} />
                    </Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item
                      name="visit_method"
                      label="方式"
                      rules={[{ required: true, message: '请选择方式' }]}
                    >
                      <Select
                        options={[
                          { label: '线下', value: '线下' },
                          { label: '线上', value: '线上' },
                        ]}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="visit_time"
                      label="家访时间"
                      rules={[{ required: true, message: '请选择时间' }]}
                    >
                      <DatePicker
                        showTime
                        style={{ width: '100%' }}
                        format="YYYY-MM-DD HH:mm"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="visit_address"
                      label="家访地址"
                    >
                      <Input placeholder="例: 北京市朝阳区XX路XX号" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="co_visitor_user_id"
                      label={
                        <Tooltip title="同组成员 (除您本人和被家访人)">
                          第二家访人 (可选)
                        </Tooltip>
                      }
                    >
                      <Select
                        allowClear
                        placeholder="选择同组成员"
                        optionFilterProp="label"
                        options={coVisitorCandidates
                          .filter((c) => c.id !== currentUserId)
                          .map((c) => ({
                            label: `${c.name} (${c.ehr_id})`,
                            value: c.id,
                          }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="is_visited"
                      label="是否已家访"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="是" unCheckedChildren="否" />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item label="扫描件 (PDF/JPG/PNG, ≤5MB)">
                  {uploadedScan ? (
                    <Space>
                      <span>已上传: {uploadedScan.file_name}</span>
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={handleRemoveScan}
                      >
                        移除
                      </Button>
                    </Space>
                  ) : (
                    <Dragger
                      name="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      beforeUpload={handleScanUpload}
                      showUploadList={false}
                      disabled={uploading}
                    >
                      <p className="ant-upload-drag-icon">
                        <InboxOutlined />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                      <p className="ant-upload-hint">仅支持 PDF / JPG / PNG, 大小不超过 5MB</p>
                    </Dragger>
                  )}
                </Form.Item>

                {/* PRD 附录 B.4 第 14 列, v2.1 明确必填。与上面的文件上传是两件事:
                    文件是"传了没有", 这个是"业务上记录表交没交"。 */}
                <Form.Item
                  name="scan_status"
                  label="家访记录表扫描件"
                  rules={[{ required: true, message: '请选择扫描件提交状态' }]}
                  extra="业务上是否已提交纸质家访记录表 (与是否上传电子文件无关)"
                >
                  <Radio.Group>
                    <Radio value="已提交">已提交</Radio>
                    <Radio value="未提交">未提交</Radio>
                  </Radio.Group>
                </Form.Item>
              </>
            )}

            {step === 1 && (
              <>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item name="team_name" label="团队名称">
                      <Input disabled />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="visit_date" label="家访日期">
                      <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="position" label="岗位">
                      <Input placeholder="例: 客户经理" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    {/* PRD B.4 第 5 列「联系电话」。P0.1 隐私裁剪把 Profile/ContactInfo
                        的电话字段全删了, 无法从档案自动回填 —— 2026-10-14 用户决定改为手填。
                        注意: 被访人本人电话按 PRD §7.1 是家访业务必需项, 不属于 B.6 的裁剪范围。 */}
                    <Form.Item name="contact_phone" label="被访人联系电话">
                      <Input placeholder="例: 13800138000" maxLength={20} />
                    </Form.Item>
                  </Col>
                </Row>

                {/* Week 3 隐私裁剪: 删除 address / mobile / home_phone */}

                {/* Week 3 隐私裁剪: 删除家属 1/家属 2 8 个字段 */}

                <Form.Item
                  name="feedback"
                  label={
                    <Space>
                      <span>反馈意见</span>
                      <Button
                        type="link"
                        size="small"
                        icon={<ThunderboltOutlined />}
                        onClick={handleFillTemplate}
                      >
                        预填七点模板
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        onClick={() => setPreviewTemplateOpen(true)}
                      >
                        查看模板
                      </Button>
                    </Space>
                  }
                >
                  <TextArea rows={6} placeholder="请填写家访反馈, 可点击'预填七点模板'快速填充" />
                </Form.Item>
              </>
            )}

            <Form.Item style={{ marginTop: 24, textAlign: 'right' }}>
              <Space>
                {step === 1 && (
                  <Button onClick={() => setStep(0)}>上一步</Button>
                )}
                {step === 0 ? (
                  <Button type="primary" onClick={handleNext}>
                    下一步
                  </Button>
                ) : (
                  <Button type="primary" loading={submitting} onClick={handleSubmit}>
                    创建草稿
                  </Button>
                )}
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Modal>

      {/* 七点模板预览 */}
      <Modal
        title="七点反馈模板 (预览)"
        open={previewTemplateOpen}
        onCancel={() => setPreviewTemplateOpen(false)}
        footer={[
          <Button
            key="fill"
            type="primary"
            onClick={() => {
              form.setFieldValue('feedback', SEVEN_POINT_TEMPLATE);
              setPreviewTemplateOpen(false);
              message.success('已预填七点反馈模板');
            }}
          >
            填入反馈
          </Button>,
          <Button key="close" onClick={() => setPreviewTemplateOpen(false)}>
            关闭
          </Button>,
        ]}
      >
        <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 4 }}>
          {SEVEN_POINT_TEMPLATE}
        </pre>
      </Modal>
    </>
  );
};

export default CreateHomeVisitModal;
