import React from 'react';
import { Typography, Card, Collapse, Divider, Space, List, Steps, Alert } from 'antd';
import { QuestionCircleOutlined, BookOutlined, ToolOutlined, TeamOutlined, FileTextOutlined, FormOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text, Link } = Typography;
const { Panel } = Collapse;
const { Step } = Steps;

const HelpPage: React.FC = () => {
  return (
    <div className="container">
      <Title level={2}>台账管理系统使用指南</Title>
      <Paragraph>
        欢迎使用台账管理系统！本系统旨在帮助企业高效管理各类台账数据，提升数据管理效率，降低管理成本。
        以下是系统的基本使用指南，帮助您快速上手。
      </Paragraph>

      <Divider />

      <Title level={3}>系统概述</Title>
      <Card>
        <Paragraph>
          台账管理系统是一个专为企业设计的综合性台账数据管理平台，支持多用户、多角色、多团队协作，
          具备完善的权限控制机制，确保数据安全可靠。
        </Paragraph>
        <Title level={4}>核心功能</Title>
        <List
          itemLayout="horizontal"
          dataSource={[
            {
              icon: <FileTextOutlined />,
              title: '台账管理',
              description: '创建、编辑、查询和导出台账数据'
            },
            {
              icon: <FormOutlined />,
              title: '模板管理',
              description: '自定义台账模板，灵活配置字段'
            },
            {
              icon: <TeamOutlined />,
              title: '用户与团队管理',
              description: '管理系统用户和团队，分配角色和权限'
            },
            {
              icon: <ToolOutlined />,
              title: '权限控制',
              description: '细粒度的权限控制，保障数据安全'
            }
          ]}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta
                avatar={item.icon}
                title={item.title}
                description={item.description}
              />
            </List.Item>
          )}
        />
      </Card>

      <Divider />

      <Title level={3}>快速入门</Title>
      <Card>
        <Steps direction="vertical" current={-1}>
          <Step 
            title="登录系统" 
            description="使用管理员提供的用户名和密码登录系统。首次登录后，建议修改初始密码。" 
          />
          <Step 
            title="熟悉界面" 
            description="系统界面主要由顶部导航栏、左侧菜单栏、内容区域和底部信息栏组成。" 
          />
          <Step 
            title="浏览首页" 
            description="首页展示系统概览，包括关键统计数据和最近台账。" 
          />
          <Step 
            title="管理台账" 
            description="在台账管理模块，您可以创建、编辑、查询和导出台账数据。" 
          />
          <Step 
            title="使用模板" 
            description="在模板管理模块，您可以创建和管理台账模板，自定义字段。" 
          />
        </Steps>
      </Card>

      <Divider />

      <Title level={3}>常见问题</Title>
      <Collapse accordion>
        <Panel header="如何创建新台账？" key="1">
          <Paragraph>
            1. 在左侧菜单中点击"台账管理"<br />
            2. 点击页面上的"创建台账"按钮<br />
            3. 选择适合的台账模板<br />
            4. 填写台账数据<br />
            5. 点击"保存"按钮完成创建
          </Paragraph>
        </Panel>
        <Panel header="如何自定义台账模板？" key="2">
          <Paragraph>
            1. 在左侧菜单中点击"模板管理"<br />
            2. 点击页面上的"创建模板"按钮<br />
            3. 填写模板名称和描述<br />
            4. 添加和配置字段（名称、类型、是否必填等）<br />
            5. 点击"保存"按钮完成创建
          </Paragraph>
        </Panel>
        <Panel header="如何管理用户权限？" key="3">
          <Paragraph>
            1. 在左侧菜单中点击"系统管理"下的"用户管理"<br />
            2. 找到目标用户，点击"编辑"按钮<br />
            3. 在编辑界面中，调整用户角色<br />
            4. 点击"保存"按钮完成修改
          </Paragraph>
          <Alert 
            message="注意" 
            description="只有具有管理员权限的用户才能管理其他用户的权限。" 
            type="info" 
            showIcon 
          />
        </Panel>
        <Panel header="忘记密码怎么办？" key="4">
          <Paragraph>
            如果您忘记了登录密码，请联系系统管理员重置密码。
          </Paragraph>
        </Panel>
        <Panel header="如何导出台账数据？" key="5">
          <Paragraph>
            1. 在台账列表中选择要导出的台账<br />
            2. 点击操作列中的"导出"按钮<br />
            3. 选择导出格式（Excel或PDF）<br />
            4. 确认导出操作
          </Paragraph>
        </Panel>
      </Collapse>

      <Divider />

      <Title level={3}>联系支持</Title>
      <Card>
        <Space direction="vertical">
          <Paragraph>
            如果您在使用过程中遇到任何问题，或有任何建议和反馈，请通过以下方式联系我们：
          </Paragraph>
          <Paragraph>
            <BookOutlined /> <Text strong>用户手册：</Text> <Link href="/docs/user-manual.pdf" target="_blank">点击下载</Link>
          </Paragraph>
          <Paragraph>
            <QuestionCircleOutlined /> <Text strong>技术支持：</Text> support@taizhang.com
          </Paragraph>
          <Paragraph>
            <Text strong>工作时间：</Text> 周一至周五 9:00-18:00
          </Paragraph>
        </Space>
      </Card>
    </div>
  );
};

export default HelpPage; 