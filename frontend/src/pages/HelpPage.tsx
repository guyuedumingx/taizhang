import React from 'react';
import { Typography, Card, Collapse, Space, List, Steps, Alert, Tabs } from 'antd';
import { 
  QuestionCircleOutlined, 
  BookOutlined, 
  ToolOutlined, 
  TeamOutlined, 
  FileTextOutlined, 
  FormOutlined,
  AuditOutlined,
  FieldBinaryOutlined,
  SettingOutlined,
  VideoCameraOutlined
} from '@ant-design/icons';
import BreadcrumbNav from '../components/common/BreadcrumbNav';

const { Title, Paragraph, Text, Link } = Typography;
const { Panel } = Collapse;
const { Step } = Steps;
const { TabPane } = Tabs;

const HelpPage: React.FC = () => {
  return (
    <>
      <BreadcrumbNav
        items={[
          { title: '帮助中心', path: '/dashboard/help' }
        ]}
        showBackButton={false}
      />
      
      <Card>
        <Title level={2}>台账管理系统使用指南</Title>
        <Paragraph>
          欢迎使用台账管理系统！本系统旨在帮助企业高效管理各类台账数据，提升数据管理效率，降低管理成本。
          以下是系统的基本使用指南，帮助您快速上手。
        </Paragraph>

        <Tabs defaultActiveKey="overview">
          <TabPane tab="系统概述" key="overview">
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
                  icon: <FieldBinaryOutlined />,
                  title: '工作流管理',
                  description: '设计和管理审批流程，提高业务效率'
                },
                {
                  icon: <AuditOutlined />,
                  title: '审批管理',
                  description: '提交和处理审批任务，跟踪审批进度'
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
          </TabPane>
          
          <TabPane tab="快速入门" key="quickstart">
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
              <Step 
                title="工作流与审批" 
                description="设置工作流并处理审批任务，实现业务流程自动化。" 
              />
              <Step 
                title="查看个人信息" 
                description="点击右上角用户头像，选择'个人中心'查看和编辑个人信息。" 
              />
            </Steps>
          </TabPane>
          
          <TabPane tab="功能指南" key="guide">
            <Collapse accordion>
              <Panel header="台账管理" key="ledger">
                <Title level={5}>创建台账</Title>
                <Paragraph>
                  1. 在左侧菜单中点击"台账管理"<br />
                  2. 点击页面上的"新建台账"按钮<br />
                  3. 选择适合的台账模板<br />
                  4. 填写台账数据<br />
                  5. 点击"保存"按钮完成创建
                </Paragraph>
                
                <Title level={5}>导出台账</Title>
                <Paragraph>
                  1. 在台账列表中找到要导出的台账<br />
                  2. 点击操作列中的"导出"按钮<br />
                  3. 选择导出格式（Excel、CSV或TXT）<br />
                  4. 确认导出操作
                </Paragraph>
                
                <Title level={5}>批量导出台账</Title>
                <Paragraph>
                  1. 在台账列表页面<br />
                  2. 点击顶部"导出"按钮<br />
                  3. 选择导出格式<br />
                  4. 系统将导出当前筛选条件下的所有台账
                </Paragraph>
              </Panel>
              
              <Panel header="模板管理" key="template">
                <Title level={5}>创建模板</Title>
                <Paragraph>
                  1. 在左侧菜单中点击"模板管理"<br />
                  2. 点击页面上的"添加模板"按钮<br />
                  3. 填写模板名称、所属部门和描述<br />
                  4. 添加和配置字段（名称、类型、是否必填等）<br />
                  5. 点击"创建"按钮完成
                </Paragraph>
                
                <Title level={5}>查看字段配置</Title>
                <Paragraph>
                  1. 在模板列表中找到目标模板<br />
                  2. 点击操作列中的"查看字段"按钮<br />
                  3. 系统将显示该模板的所有字段配置
                </Paragraph>
                
                <Title level={5}>关联工作流</Title>
                <Paragraph>
                  1. 在模板列表中找到目标模板<br />
                  2. 点击操作列中的"关联工作流"按钮<br />
                  3. 在工作流列表中创建或选择关联的工作流
                </Paragraph>
              </Panel>
              
              <Panel header="工作流管理" key="workflow">
                <Title level={5}>创建工作流</Title>
                <Paragraph>
                  1. 在左侧菜单中点击"工作流管理"<br />
                  2. 点击页面上的"新建工作流"按钮<br />
                  3. 填写工作流名称、描述和选择关联模板<br />
                  4. 配置工作流节点（开始、审批、结束等）<br />
                  5. 为审批节点设置审批人/角色<br />
                  6. 点击"创建"按钮完成
                </Paragraph>
                
                <Title level={5}>查看工作流详情</Title>
                <Paragraph>
                  1. 在工作流列表中找到目标工作流<br />
                  2. 点击操作列中的查看按钮<br />
                  3. 系统将显示工作流的详细信息和节点配置
                </Paragraph>
              </Panel>
              
              <Panel header="审批任务" key="approval">
                <Title level={5}>提交审批</Title>
                <Paragraph>
                  1. 在台账详情页面<br />
                  2. 点击"提交审批"按钮<br />
                  3. 确认提交后，系统将启动相关工作流
                </Paragraph>
                
                <Title level={5}>处理审批任务</Title>
                <Paragraph>
                  1. 在左侧菜单中点击"审批任务"<br />
                  2. 在待办任务列表中找到需要处理的任务<br />
                  3. 点击"查看"按钮查看详情<br />
                  4. 选择"通过"或"拒绝"操作<br />
                  5. 输入审批意见并确认
                </Paragraph>
              </Panel>
              
              <Panel header="个人信息管理" key="profile">
                <Title level={5}>查看个人信息</Title>
                <Paragraph>
                  1. 点击右上角用户头像<br />
                  2. 在下拉菜单中选择"个人中心"<br />
                  3. 查看个人基本信息
                </Paragraph>
                
                <Title level={5}>编辑个人信息</Title>
                <Paragraph>
                  1. 在个人中心页面<br />
                  2. 点击"编辑资料"按钮<br />
                  3. 修改相关信息<br />
                  4. 点击"保存"按钮完成
                </Paragraph>
                
                <Title level={5}>修改密码</Title>
                <Paragraph>
                  1. 在个人中心页面<br />
                  2. 点击"修改密码"按钮<br />
                  3. 输入原密码和新密码<br />
                  4. 确认修改
                </Paragraph>
              </Panel>
            </Collapse>
          </TabPane>
          
          <TabPane tab="常见问题" key="faq">
            <Collapse accordion>
              <Panel header="如何重置密码？" key="1">
                <Paragraph>
                  如果您忘记了登录密码，请联系系统管理员重置密码。管理员重置后，您将收到临时密码，首次登录后需要立即修改密码。
                </Paragraph>
              </Panel>
              <Panel header="怎样给团队添加成员？" key="2">
                <Paragraph>
                  1. 在左侧菜单中点击"系统管理"下的"团队管理"<br />
                  2. 找到目标团队，点击"成员"按钮<br />
                  3. 在团队成员页面，点击"添加成员"按钮<br />
                  4. 选择要添加的用户<br />
                  5. 点击"确定"按钮完成添加
                </Paragraph>
                <Alert 
                  message="注意" 
                  description="只有具有团队管理权限的用户才能管理团队成员。" 
                  type="info" 
                  showIcon 
                />
              </Panel>
              <Panel header="台账提交后可以修改吗？" key="3">
                <Paragraph>
                  台账提交审批后，通常不能再修改。如果需要修改，您有两种选项：
                  <br />1. 如果审批尚未完成，请联系当前审批人拒绝该台账，台账将回到草稿状态
                  <br />2. 如果审批已完成，请创建一个新台账或联系系统管理员处理
                </Paragraph>
              </Panel>
              <Panel header="如何查看操作日志？" key="4">
                <Paragraph>
                  1. 在左侧菜单中点击"日志管理"<br />
                  2. 选择"系统日志"或"审计日志"标签<br />
                  3. 使用搜索条件筛选所需日志<br />
                  4. 查看日志详情
                </Paragraph>
                <Alert 
                  message="注意" 
                  description="只有具有日志查看权限的用户才能访问日志管理功能。" 
                  type="info" 
                  showIcon 
                />
              </Panel>
              <Panel header="系统支持哪些类型的导出格式？" key="5">
                <Paragraph>
                  系统目前支持以下导出格式：
                  <br />• Excel格式(.xlsx)：适合进一步处理和分析数据
                  <br />• CSV格式(.csv)：适合导入其他系统
                  <br />• TXT格式(.txt)：适合简单文本查看
                </Paragraph>
              </Panel>
            </Collapse>
          </TabPane>
          
          <TabPane tab="视频教程" key="video">
            <List
              itemLayout="horizontal"
              dataSource={[
                {
                  title: '系统快速入门',
                  description: '5分钟了解系统基本功能和操作流程',
                  link: '#'
                },
                {
                  title: '台账管理详解',
                  description: '详细讲解台账的创建、编辑、查询和导出',
                  link: '#'
                },
                {
                  title: '模板设计指南',
                  description: '如何设计高效实用的台账模板',
                  link: '#'
                },
                {
                  title: '工作流配置教程',
                  description: '设置工作流审批流程的详细步骤',
                  link: '#'
                },
                {
                  title: '权限管理实战',
                  description: '如何配置用户权限，保障数据安全',
                  link: '#'
                }
              ]}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<VideoCameraOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                    title={<Link href={item.link}>{item.title}</Link>}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
            <Alert 
              message="提示" 
              description="视频教程功能正在建设中，将在系统更新后上线。" 
              type="info" 
              showIcon 
              style={{ marginTop: 16 }}
            />
          </TabPane>
          
          <TabPane tab="联系我们" key="contact">
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
                  <SettingOutlined /> <Text strong>系统版本：</Text> v2.0.1
                </Paragraph>
                <Paragraph>
                  <Text strong>工作时间：</Text> 周一至周五 9:00-18:00
                </Paragraph>
              </Space>
            </Card>
          </TabPane>
        </Tabs>
      </Card>
    </>
  );
};

export default HelpPage; 