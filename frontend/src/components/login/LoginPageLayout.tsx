import React, { ReactNode } from 'react';
import { Typography } from 'antd';
import BOCLogo from './BOCLogo';

const { Title, Paragraph, Text } = Typography;

interface LoginPageLayoutProps {
  children: ReactNode;
}

const LoginPageLayout: React.FC<LoginPageLayoutProps> = ({ children }) => {
  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-left-content">
          <div className="login-branding">
            <BOCLogo />
            <Title level={2} className="bank-name">中国银行</Title>
          </div>
          <div className="login-intro">
            <Title level={3}>台账管理系统</Title>
            <Paragraph className="subtitle">集约运营中心（广东）</Paragraph>
            <Paragraph className="description">
              高效、安全的台账管理平台，提供数据管理与分析服务。
            </Paragraph>
          </div>
        </div>
      </div>
      <div className="login-right">
        {children}
      </div>
    </div>
  );
};

export default LoginPageLayout; 