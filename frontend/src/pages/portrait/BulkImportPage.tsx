/**
 * 数字画像-批量导入 D1 (PRD §8.1)
 *
 * 3 个 Tab:
 *   - 出入境批量导入 (17 列, 模块 2.1 实现后启用)
 *   - 消防演练批量导入 (6 列, 模块 2.2 实现后启用)
 *   - 培训记录批量导入 (5 必填 + 2 选填, 当前可用)
 *
 * 每个 Tab 含: 模板下载 + 上传 + 结果反馈
 */
import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Button,
  Upload,
  Table,
  Alert,
  Space,
  Typography,
  message,
  Spin,
  Result,
} from 'antd';
import {
  DownloadOutlined,
  InboxOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import { api } from '../../api';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;
const { Dragger } = Upload;

// ============================================================================
// 模板列定义 (与后端 routers/templates.py + routers/training.py 保持一致)
// ============================================================================
const TEMPLATES = {
  'entry-exit': {
    label: '出入境台账',
    headers: [
      '姓名', '团队', '职务', '证照号', '出境原因', '目的地',
      '申请离境', '申请返回', '证照类别', '申请类型', '团队审批人',
      '实际出境', '实际返回', '年份', '组别', '备注', 'EHR号',
    ],
    description: 'PRD §10.1 F9 出入境批量导入 (17 列)',
    apiPath: '/portrait/templates/excel/entry-exit',
    importPath: '/portrait/entry-exit/import',
    enabled: true,
  },
  drill: {
    label: '消防演练',
    headers: ['活动日期', '演练类型', '地点', 'EHR号', '姓名', '是否参与'],
    description: 'PRD §10.2 F3 消防演练批量导入 (6 列)',
    apiPath: '/portrait/templates/excel/drill',
    importPath: '/portrait/drills/import',
    enabled: true,
  },
  training: {
    label: '培训记录',
    headers: ['EHR号', '培训名', '培训时间', '培训类型', '培训机构', '证书编号', '有效期'],
    description: 'PRD §10.3 培训批量导入 (5 必填 + 2 选填)',
    apiPath: '/portrait/templates/excel/training',
    importPath: '/portrait/training/import',
    enabled: true,
  },
} as const;

type TemplateKey = keyof typeof TEMPLATES;

interface ImportResult {
  success_count: number;
  failed_count: number;
  failed_rows: Array<{ row_number: number; ehr_id: string; reason: string }>;
}

// ============================================================================
// 单 Tab 内容
// ============================================================================
const ImportTab: React.FC<{ template: typeof TEMPLATES[TemplateKey] }> = ({ template }) => {
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const downloadTemplate = async () => {
    try {
      const response = await api.get(template.apiPath, { responseType: 'blob' });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template.label}_导入模板.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('模板下载已开始');
    } catch (err: any) {
      message.error(`模板下载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls,.csv',
    multiple: false,
    showUploadList: false,
    beforeUpload: async (file: UploadFile) => {
      if (!template.enabled || !template.importPath) {
        message.warning(`${template.label} 导入端点尚未实现, 请等待后续版本`);
        return false;
      }
      setImporting(true);
      setResult(null);
      const formData = new FormData();
      formData.append('file', file as any);
      try {
        const response = await api.post(template.importPath, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setResult(response.data);
        if (response.data.failed_count === 0) {
          message.success(`导入成功: ${response.data.success_count} 条`);
        } else if (response.data.success_count === 0) {
          message.error(`导入失败: ${response.data.failed_count} 条全部失败`);
        } else {
          message.warning(`部分成功: ${response.data.success_count} 条, 失败 ${response.data.failed_count} 条`);
        }
      } catch (err: any) {
        message.error(`导入失败: ${err?.response?.data?.detail || err.message}`);
      } finally {
        setImporting(false);
      }
      return false;  // 阻止 antd 默认上传
    },
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* 描述 + 模板下载 */}
      <Card size="small" type="inner">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>{template.description}</Text>
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={downloadTemplate}
              type="primary"
              ghost
            >
              下载 Excel 模板
            </Button>
            {!template.enabled && (
              <Alert
                type="info"
                showIcon
                message="该模块的导入功能将在后续版本启用, 当前可下载模板预览格式"
                style={{ flex: 1 }}
              />
            )}
          </Space>
        </Space>
      </Card>

      {/* 字段说明表 */}
      <Card size="small" title="字段说明" type="inner">
        <Table
          size="small"
          pagination={false}
          rowKey={(_r, idx) => String(idx)}
          dataSource={template.headers.map((h, idx) => ({
            idx: idx + 1,
            name: h,
            required: idx < 5 || template.headers.slice(0, 5).includes(h),
          }))}
          columns={[
            { title: '#', dataIndex: 'idx', width: 50 },
            { title: '字段名', dataIndex: 'name' },
            {
              title: '是否必填',
              dataIndex: 'required',
              width: 100,
              render: (v: boolean) =>
                v ? (
                  <Text type="danger">必填</Text>
                ) : (
                  <Text type="secondary">选填</Text>
                ),
            },
          ]}
        />
      </Card>

      {/* 上传区 */}
      <Card size="small" title="上传文件" type="inner">
        <Spin spinning={importing}>
          <Dragger {...uploadProps} disabled={!template.enabled}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 Excel / CSV 文件到此区域上传</p>
            <p className="ant-upload-hint">支持 .xlsx / .xls / .csv 格式</p>
          </Dragger>
        </Spin>
      </Card>

      {/* 反馈结果 */}
      {result && (
        <Card size="small" type="inner">
          {result.failed_count === 0 ? (
            <Result
              status="success"
              icon={<CheckCircleOutlined />}
              title={`导入成功: ${result.success_count} 条`}
              subTitle="所有记录已成功导入"
            />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Result
                status={result.success_count === 0 ? 'error' : 'warning'}
                icon={<CloseCircleOutlined />}
                title={`成功 ${result.success_count} 条, 失败 ${result.failed_count} 条`}
                subTitle="请检查失败行后修正重新上传"
              />
              <Table
                size="small"
                rowKey={(_r, idx) => String(idx)}
                pagination={{ pageSize: 10 }}
                dataSource={result.failed_rows}
                columns={[
                  { title: '行号', dataIndex: 'row_number', width: 80 },
                  { title: 'EHR号', dataIndex: 'ehr_id', width: 120 },
                  { title: '失败原因', dataIndex: 'reason' },
                ]}
              />
            </Space>
          )}
        </Card>
      )}
    </Space>
  );
};

// ============================================================================
// 主页面
// ============================================================================
const BulkImportPage: React.FC = () => {
  return (
    <div>
      <BreadcrumbNav
        items={[
          { title: '数字画像', path: '/dashboard/portrait/profile' },
          { title: '批量导入' },
        ]}
      />
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>批量导入 (D1)</Title>
            <Text type="secondary">管理员专属</Text>
          </Space>
        }
      >
        <Tabs
          defaultActiveKey="training"
          items={(Object.keys(TEMPLATES) as TemplateKey[]).map((key) => ({
            key,
            label: TEMPLATES[key].label,
            children: <ImportTab template={TEMPLATES[key]} />,
          }))}
        />
      </Card>
    </div>
  );
};

export default BulkImportPage;