import React from 'react';
import { Divider, Typography } from 'antd';

const { Text, Paragraph } = Typography;

const SecurityTips: React.FC = () => {
  return (
    <>
      <Divider plain>
        <Text type="secondary">安全登录提示</Text>
      </Divider>
      
      <Paragraph className="security-tips" type="secondary">
        为了保障您的账号安全，请不要共享密码，登录后请及时退出。
      </Paragraph>
      
      <div className="login-footer">
        <Text type="secondary">© {new Date().getFullYear()} 中国银行集约运营中心（广东）台账管理系统</Text>
      </div>
    </>
  );
};

export default SecurityTips; 