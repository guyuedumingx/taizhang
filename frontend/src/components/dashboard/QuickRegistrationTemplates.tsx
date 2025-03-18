import React from 'react';
import { Row, Col, Card, Button, Typography, Tooltip, Empty } from 'antd';
import { FormOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { Template } from '../../types';

const { Title, Paragraph } = Typography;

interface QuickRegistrationTemplatesProps {
  templates: Template[];
  loading: boolean;
  onTemplateSelect: (templateId: number) => void;
}

const QuickRegistrationTemplates: React.FC<QuickRegistrationTemplatesProps> = ({
  templates,
  loading,
  onTemplateSelect
}) => {
  const navigate = useNavigate();

  return (
    <>
      <div className="page-header">
        <Title level={4} className="page-title">
          快速登记台账
        </Title>
        <Button 
          type="link" 
          onClick={() => navigate('/dashboard/templates')}
        >
          管理模板
        </Button>
      </div>
      
      <Paragraph style={{ marginBottom: 16 }}>
        选择模板类型，快速创建对应台账
      </Paragraph>
      
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {loading ? (
          <Col span={24}>
            <Card loading={true} />
          </Col>
        ) : templates.length > 0 ? (
          templates.slice(0, 8).map(template => (
            <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
              <Card 
                hoverable 
                className="template-card"
                onClick={() => onTemplateSelect(template.id)}
                style={{ height: '100%' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ flex: '1 0 auto' }}>
                    <div style={{ fontSize: 36, color: 'var(--primary-color)', textAlign: 'center', marginBottom: 12 }}>
                      <FormOutlined />
                    </div>
                    <Tooltip title={template.name}>
                      <Title level={5} ellipsis={{ rows: 1 }} style={{ textAlign: 'center' }}>
                        {template.name}
                      </Title>
                    </Tooltip>
                  </div>
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0, fontSize: 12 }}>
                    {template.description || '无描述'}
                  </Paragraph>
                  <div style={{ marginTop: 12, textAlign: 'center' }}>
                    <Button type="primary" size="small">
                      创建台账
                    </Button>
                  </div>
                </div>
              </Card>
            </Col>
          ))
        ) : (
          <Col span={24}>
            <Empty description="暂无模板，请先创建模板" />
          </Col>
        )}
        {templates.length > 8 && (
          <Col span={24} style={{ textAlign: 'center', marginTop: 8 }}>
            <Button type="link" onClick={() => navigate('/dashboard/templates')}>
              查看更多模板
            </Button>
          </Col>
        )}
      </Row>
    </>
  );
};

export default QuickRegistrationTemplates; 