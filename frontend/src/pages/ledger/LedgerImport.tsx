import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Form,
  message,
  Result,
  Select,
  Space,
  Spin,
  Statistic,
  Steps,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  DownloadOutlined,
  InboxOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { Template, Team } from '../../types';
import { TemplateService } from '../../services/TemplateService';
import { TeamService } from '../../services/TeamService';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import {
  commitImport,
  downloadImportTemplate,
  ImportCommitResult,
  ImportIssue,
  ImportValidationReport,
  validateImport,
} from '../../api/ledgerImport';

const { Title, Text } = Typography;
const { Dragger } = Upload;
const { Step } = Steps;

const ISSUE_TYPE_LABEL: Record<string, string> = {
  missing_required: '必填缺失',
  duplicate: '重复',
  team_not_found: '团队不存在',
  user_not_found: '柜员号不存在',
  uncleanable_value: '无法清洗',
  type_mismatch: '类型错误',
  row_limit_exceeded: '行数超限',
  extra_column: '未知列',
};

// 格式化原始值:空值/缺失统一显示 (空),其余 toString
const formatRaw = (v: unknown): string => {
  if (v === null || v === undefined || v === '') return '(空)';
  return String(v);
};

const LedgerImport: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();

  const [currentStep, setCurrentStep] = useState(0);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [report, setReport] = useState<ImportValidationReport | null>(null);
  const [commitResult, setCommitResult] = useState<ImportCommitResult | null>(null);

  useEffect(() => {
    if (!hasPermission(PERMISSIONS.LEDGER_IMPORT)) {
      message.warning('没有台账导入权限');
      navigate('/dashboard/ledgers');
      return;
    }
    loadMeta();
  }, []);

  const loadMeta = async () => {
    try {
      const [tpls, tms] = await Promise.all([
        TemplateService.getTemplates(),
        TeamService.getTeams(),
      ]);
      setTemplates(tpls || []);
      setTeams(tms || []);
    } catch (err) {
      message.error('加载模板/团队列表失败');
    }
  };

  const handleDownloadTemplate = async () => {
    if (!templateId) {
      message.warning('请先选择模板');
      return;
    }
    setDownloading(true);
    try {
      const blob = await downloadImportTemplate(templateId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `import_template_${templateId}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '下载模板失败');
    } finally {
      setDownloading(false);
    }
  };

  const handleValidate = async () => {
    if (!templateId || !file) {
      message.warning('请先选择模板并上传文件');
      return;
    }
    setValidating(true);
    try {
      const r = await validateImport(templateId, file, teamId ?? undefined);
      setReport(r);
      setCurrentStep(2);
      if (r.importable_count === 0) {
        message.warning('没有可导入的行,请检查问题清单');
      } else {
        message.success(`预校验完成:可导入 ${r.importable_count} 行,问题 ${r.problem_rows} 行`);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : '预校验失败');
    } finally {
      setValidating(false);
    }
  };

  const handleCommit = async () => {
    if (!templateId || !file) return;
    setCommitting(true);
    try {
      const r = await commitImport(templateId, file, teamId ?? undefined);
      setCommitResult(r);
      setCurrentStep(3);
      if (r.failed_count > 0) {
        message.warning(`导入完成:成功 ${r.success_count} 条,失败 ${r.failed_count} 条`);
      } else {
        message.success(`导入完成:成功 ${r.success_count} 条`);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : '导入失败');
    } finally {
      setCommitting(false);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setFile(null);
    setReport(null);
    setCommitResult(null);
    setTemplateId(null);
    setTeamId(null);
    form.resetFields();
  };

  const { headerIssues, rowIssuesByRow } = useMemo(() => {
    if (!report) return { headerIssues: [], rowIssuesByRow: [] };
    const headers: ImportIssue[] = [];
    const byRow = new Map<number, ImportIssue[]>();
    for (const issue of report.issues) {
      if (issue.row === 0) {
        headers.push(issue);
      } else {
        const list = byRow.get(issue.row) || [];
        list.push(issue);
        byRow.set(issue.row, list);
      }
    }
    // 按行号升序,行内按 field 字典序(空 field 排后面)
    const sorted = Array.from(byRow.entries())
      .sort(([a], [b]) => a - b)
      .map(([row, items]) => ({
        row,
        items: [...items].sort((x, y) => {
          const fx = x.field || '';
          const fy = y.field || '';
          if (!fx && fy) return 1;
          if (fx && !fy) return -1;
          return fx.localeCompare(fy, 'zh-CN');
        }),
      }));
    return { headerIssues: headers, rowIssuesByRow: sorted };
  }, [report]);

  return (
    <div style={{ padding: 24 }}>
      <BreadcrumbNav
        items={[
          { title: '台账管理' },
          { title: '台账导入' },
        ]}
      />
      <Title level={3} style={{ marginTop: 8 }}>台账导入</Title>

      <Card style={{ marginTop: 16 }}>
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="选择模板" description="下载导入模板" />
          <Step title="上传文件" description="选择填好的 Excel" />
          <Step title="校验报告" description="确认后导入" />
          <Step title="导入结果" description="查看批次信息" />
        </Steps>

        {/* Step 0: 选择模板 */}
        {currentStep === 0 && (
          <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
            <Form.Item label="选择台账模板" required>
              <Select
                placeholder="请选择要导入的台账模板"
                value={templateId}
                onChange={(v) => setTemplateId(v)}
                options={templates.map((t) => ({ label: t.name, value: t.id }))}
                showSearch
                optionFilterProp="label"
              />
            </Form.Item>
            <Form.Item label="所属团队(可选,作为组别反查失败的兜底)">
              <Select
                placeholder="选择团队"
                value={teamId}
                onChange={(v) => setTeamId(v)}
                options={teams.map((t) => ({ label: t.name, value: t.id }))}
                allowClear
                showSearch
                optionFilterProp="label"
              />
            </Form.Item>
            <Space>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownloadTemplate}
                loading={downloading}
                disabled={!templateId}
              >
                下载导入模板
              </Button>
              <Button
                type="primary"
                disabled={!templateId}
                onClick={() => setCurrentStep(1)}
              >
                下一步:上传文件
              </Button>
            </Space>
          </Form>
        )}

        {/* Step 1: 上传文件 */}
        {currentStep === 1 && (
          <div>
            <Dragger
              accept=".xlsx"
              maxCount={1}
              beforeUpload={(f) => {
                setFile(f);
                return false; // 阻止自动上传
              }}
              onRemove={() => setFile(null)}
              fileList={file ? [{ uid: '-1', name: file.name }] : []}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽上传填好的 Excel 文件</p>
              <p className="ant-upload-hint">仅支持 .xlsx,行数不超过 5000</p>
            </Dragger>
            <Space style={{ marginTop: 16 }}>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重新选择模板
              </Button>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleValidate}
                loading={validating}
                disabled={!file}
              >
                开始校验
              </Button>
            </Space>
          </div>
        )}

        {/* Step 2: 校验报告 */}
        {currentStep === 2 && report && (
          <div>
            <div style={{ display: 'flex', gap: 24, marginBottom: 24, flexWrap: 'wrap' }}>
              <Card style={{ minWidth: 160 }}>
                <Statistic title="总行数" value={report.total_rows} />
              </Card>
              <Card style={{ minWidth: 160 }}>
                <Statistic
                  title="可导入"
                  value={report.importable_count}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
              <Card style={{ minWidth: 160 }}>
                <Statistic
                  title="可自动清洗"
                  value={report.cleanable_count}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
              <Card style={{ minWidth: 160 }}>
                <Statistic
                  title="问题行"
                  value={report.problem_rows}
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </div>

            {report.row_limit_warning && (
              <Card style={{ marginBottom: 16, background: '#fffbe6' }}>
                <Text type="warning">{report.row_limit_warning}</Text>
              </Card>
            )}

            {/* 表头问题 banner(row=0) */}
            {headerIssues.length > 0 && (
              <Card
                size="small"
                style={{ marginBottom: 16, background: '#fffbe6', borderColor: '#ffe58f' }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text strong type="warning">
                    ⚠️ 表头问题({headerIssues.length})
                  </Text>
                  {headerIssues.map((issue, idx) => (
                    <Text key={idx} type="warning">
                      • {issue.field || ISSUE_TYPE_LABEL[issue.type] || issue.type} — {issue.reason}
                    </Text>
                  ))}
                </Space>
              </Card>
            )}

            {/* 问题行清单:按行分组,平铺全部明细 */}
            <Card
              size="small"
              title={`问题行清单(${rowIssuesByRow.length})`}
              style={{ marginBottom: 16 }}
            >
              {rowIssuesByRow.length === 0 ? (
                <Text type="secondary">无问题行 ✓</Text>
              ) : (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  {rowIssuesByRow.map(({ row, items }) => (
                    <div
                      key={row}
                      style={{
                        borderLeft: '3px solid #cf1322',
                        paddingLeft: 12,
                        paddingTop: 4,
                        paddingBottom: 4,
                      }}
                    >
                      <Text strong style={{ color: '#cf1322' }}>
                        第 {row} 行 · 共 {items.length} 个问题
                      </Text>
                      <div style={{ marginTop: 6 }}>
                        {items.map((issue, idx) => (
                          <div key={idx} style={{ marginBottom: 4 }}>
                            <Text strong>
                              {issue.field || ISSUE_TYPE_LABEL[issue.type] || issue.type}
                            </Text>
                            <Text> — {issue.reason}</Text>
                            <Text type="secondary">（原始值: {formatRaw(issue.raw)}）</Text>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </Space>
              )}
            </Card>

            {/* 可清洗预览:辅助信息,不属于问题行 */}
            {report.cleanable_previews.length > 0 && (
              <Card
                size="small"
                title={`可自动清洗(${report.cleanable_previews.length})`}
                style={{ marginBottom: 16 }}
              >
                <Table
                  rowKey={(r) => `${r.row}-${r.field}`}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: '行号', dataIndex: 'row', width: 80 },
                    { title: '字段', dataIndex: 'field', width: 140 },
                    { title: '原始值', dataIndex: 'raw', render: (v) => formatRaw(v) },
                    { title: '清洗后', dataIndex: 'clean', render: (v) => String(v) },
                  ]}
                  dataSource={report.cleanable_previews}
                />
              </Card>
            )}

            <Space style={{ marginTop: 16 }}>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重新上传
              </Button>
              <Button
                type="primary"
                onClick={handleCommit}
                loading={committing}
                disabled={report.importable_count === 0}
              >
                确认导入 {report.importable_count} 条
              </Button>
            </Space>
          </div>
        )}

        {/* Step 3: 导入结果 */}
        {currentStep === 3 && commitResult && (
          <Result
            status={commitResult.failed_count > 0 ? 'warning' : 'success'}
            title={`导入完成:成功 ${commitResult.success_count} 条,失败 ${commitResult.failed_count} 条`}
            subTitle={
              <Space direction="vertical" align="start">
                <Text>批次号:{commitResult.batch_id}</Text>
                <Text>用时:{commitResult.elapsed_seconds} 秒</Text>
                {commitResult.failed_count > 0 && commitResult.failures_download_url && (
                  <Text type="warning">
                    有 {commitResult.failed_count} 条失败,可在导入历史中下载失败清单
                  </Text>
                )}
              </Space>
            }
            extra={[
              <Button key="list" onClick={() => navigate('/dashboard/ledgers')}>
                回到列表
              </Button>,
              <Button key="history" onClick={() => navigate('/dashboard/ledgers/import-history')}>
                查看导入历史
              </Button>,
              <Button key="again" type="primary" onClick={handleReset}>
                再导一批
              </Button>,
            ]}
          />
        )}
      </Card>
    </div>
  );
};

export default LedgerImport;
