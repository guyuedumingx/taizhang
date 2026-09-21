import React, { useEffect, useState } from 'react';
import { Card, Col, Descriptions, Empty, Row, Spin, Tag, Typography, Anchor, message } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { getMyPortraitProfile } from '../../api/portraitProfiles';
import {
  PortraitProfileFull,
} from '../../types';

const { Title, Text } = Typography;

const TAG_COLORS = ['green', 'purple', 'blue', 'orange', 'cyan', 'magenta', 'gold', 'geekblue'];

// 展示型字段（label: value）
const F: React.FC<{ label: string; value?: React.ReactNode }> = ({ label, value }) => (
  <div style={{ display: 'flex', gap: 6, fontSize: 13, lineHeight: '22px' }}>
    <span style={{ color: '#8c8c8c', flexShrink: 0 }}>{label}：</span>
    <span style={{ color: '#333' }}>{value ?? '—'}</span>
  </div>
);

// 通用子表区块：无数据时显示占位
const SectionTable: React.FC<{
  columns: { title: string; dataIndex: string; render?: (v: any, r?: any) => React.ReactNode }[];
  rows: any[];
}> = ({ columns, rows }) => {
  if (!rows.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />;
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.dataIndex} style={{ textAlign: 'left', padding: '8px 12px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', fontWeight: 500 }}>
              {c.title}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.id ?? i}>
            {columns.map((c) => (
              <td key={c.dataIndex} style={{ padding: '10px 12px', borderBottom: '1px solid #f0f0f0' }}>
                {c.render ? c.render(r[c.dataIndex], r) : (r[c.dataIndex] ?? '—')}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

const dateStr = (v?: string | null) => (v ? v.substring(0, 10) : undefined);

const MyProfile: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<PortraitProfileFull | null>(null);

  useEffect(() => {
    getMyPortraitProfile()
      .then(setProfile)
      .catch((e) => {
        console.error('获取档案失败:', e);
        message.error('获取档案失败');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  if (!profile) return <Empty description="档案数据为空" style={{ padding: 48 }} />;

  const b = profile.base;
  const anchorItems = [
    { key: 'base', href: '#p-base', title: '基础信息' },
    { key: 'tags', href: '#p-tags', title: '技能标签' },
    { key: 'political', href: '#p-political', title: '政治面貌' },
    { key: 'education', href: '#p-education', title: '学历学位' },
    { key: 'family', href: '#p-family', title: '家庭关系' },
    { key: 'resume', href: '#p-resume', title: '简历' },
    { key: 'reward', href: '#p-reward', title: '奖惩信息' },
    { key: 'qualification', href: '#p-qualification', title: '资格证书' },
    { key: 'projects', href: '#p-projects', title: '项目总结' },
    { key: 'achievement', href: '#p-achievement', title: '专业成果' },
    { key: 'language', href: '#p-language', title: '语言能力' },
    { key: 'contact', href: '#p-contact', title: '通讯信息' },
    { key: 'intent', href: '#p-intent', title: '发展意向' },
  ];

  const sectionCard = (id: string, title: string, extra: React.ReactNode = undefined, children: React.ReactNode = null) => (
    <Card
      id={id}
      size="small"
      title={<span style={{ fontWeight: 600 }}>{title}</span>}
      extra={extra}
      style={{ marginBottom: 16, borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
    >
      {children}
    </Card>
  );

  return (
    <div>
      <BreadcrumbNav
        items={[
          { title: '数字画像' },
          { title: '我的档案' },
        ]}
      />
      <Row gutter={16}>
        <Col flex="auto" style={{ minWidth: 0, maxWidth: 920 }}>
          <Title level={4} style={{ marginTop: 0 }}>我的档案</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>维护个人档案信息（修改功能将随审批流上线）</Text>

          <div style={{ marginTop: 16 }}>
            {sectionCard('p-base', '基础信息',
              b?.is_emergency_staff ? (
                <Tag color="red" icon={<SafetyOutlined />} style={{ borderRadius: 20 }}>应急先锋队</Tag>
              ) : undefined,
              <>
                <Row gutter={[16, 10]}>
                  <Col span={8}><F label="姓名" value={profile.name} /></Col>
                  <Col span={8}><F label="EHR 号" value={profile.ehr_no} /></Col>
                  <Col span={8}><F label="组别" value={profile.group_name} /></Col>
                </Row>
                <div style={{ borderTop: '1px dashed #f0f0f0', margin: '12px 0' }} />
                <Row gutter={[16, 10]}>
                  <Col span={8}><F label="性别" value={b?.gender} /></Col>
                  <Col span={8}><F label="民族" value={b?.nation} /></Col>
                  <Col span={8}><F label="出生日期" value={dateStr(b?.birth_date)} /></Col>
                  <Col span={8}><F label="职位" value={b?.job_title} /></Col>
                  <Col span={8}><F label="婚姻状况" value={b?.marital_status} /></Col>
                  <Col span={8}><F label="参加工作时间" value={dateStr(b?.work_start_date)} /></Col>
                  <Col span={8}><F label="证件类型" value={b?.id_type} /></Col>
                  <Col span={8}><F label="证件号码" value={b?.id_number} /></Col>
                  <Col span={8}><F label="籍贯" value={b?.native_place} /></Col>
                  <Col span={8}><F label="出生地" value={b?.birth_place} /></Col>
                  <Col span={8}><F label="户籍所在地" value={b?.household_place} /></Col>
                  <Col span={8}><F label="入职日期" value={dateStr(b?.hire_date)} /></Col>
                </Row>
              </>
            )}

            {sectionCard('p-tags', '技能标签',
              <span style={{ fontSize: 12, color: '#8c8c8c' }}>{profile.skill_tags.length} 个</span>,
              profile.skill_tags.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {profile.skill_tags.map((t, i) => (
                    <Tag key={t.id} color={TAG_COLORS[i % TAG_COLORS.length]} style={{ borderRadius: 4, padding: '3px 10px' }}>
                      {t.tag_name}
                    </Tag>
                  ))}
                </div>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无标签" />
            )}

            {sectionCard('p-political', '政治面貌', undefined,
              <SectionTable
                rows={profile.political}
                columns={[
                  { title: '政治面貌', dataIndex: 'political_status' },
                  { title: '参加日期', dataIndex: 'join_date', render: dateStr },
                  { title: '介绍人', dataIndex: 'introducer' },
                ]}
              />
            )}

            {sectionCard('p-education', '学历学位', undefined,
              <SectionTable
                rows={profile.education}
                columns={[
                  { title: '学历', dataIndex: 'education_level' },
                  { title: '学位', dataIndex: 'degree' },
                  { title: '教育类别', dataIndex: 'education_category' },
                  { title: '学校', dataIndex: 'school' },
                  { title: '专业', dataIndex: 'major_name' },
                  { title: '入学时间', dataIndex: 'enrollment_date', render: dateStr },
                  { title: '毕业时间', dataIndex: 'graduation_date', render: dateStr },
                ]}
              />
            )}

            {sectionCard('p-family', '家庭关系', undefined,
              <SectionTable
                rows={profile.family}
                columns={[
                  { title: '姓名', dataIndex: 'name' },
                  { title: '关系', dataIndex: 'relation' },
                  { title: '性别', dataIndex: 'gender' },
                  { title: '出生日期', dataIndex: 'birth_date', render: dateStr },
                  { title: '工作单位及职务', dataIndex: 'work_unit_and_title' },
                  { title: '政治面貌', dataIndex: 'political_status' },
                  { title: '人员状况', dataIndex: 'employment_status' },
                ]}
              />
            )}

            {sectionCard('p-resume', '简历', undefined,
              <SectionTable
                rows={profile.resume}
                columns={[
                  { title: '开始时间', dataIndex: 'start_time', render: dateStr },
                  { title: '结束时间', dataIndex: 'end_time', render: dateStr },
                  { title: '工作单位及职务', dataIndex: 'unit_and_title' },
                ]}
              />
            )}

            {sectionCard('p-reward', '奖惩信息', undefined,
              <SectionTable
                rows={profile.reward}
                columns={[
                  { title: '类型', dataIndex: 'reward_type', render: (v) => (v ? <Tag color={v === '奖励' ? 'green' : 'red'}>{v}</Tag> : '—') },
                  { title: '时间', dataIndex: 'reward_time', render: dateStr },
                  { title: '名称', dataIndex: 'reward_name' },
                  { title: '原因', dataIndex: 'reward_reason' },
                ]}
              />
            )}

            {sectionCard('p-qualification', '资格证书', undefined,
              <SectionTable
                rows={profile.qualification}
                columns={[
                  { title: '资格名称', dataIndex: 'qualification_name' },
                  { title: '取得时间', dataIndex: 'obtain_time', render: dateStr },
                  { title: '有效期', dataIndex: 'valid_until', render: dateStr },
                ]}
              />
            )}

            {sectionCard('p-projects', '项目总结', undefined,
              <SectionTable
                rows={profile.project_summaries}
                columns={[
                  { title: '项目名称', dataIndex: 'project_name' },
                  { title: '开始时间', dataIndex: 'start_time', render: dateStr },
                  { title: '结束时间', dataIndex: 'end_time', render: dateStr },
                  { title: '角色', dataIndex: 'role' },
                  { title: '描述', dataIndex: 'description' },
                  {
                    title: '关联标签', dataIndex: 'tag_names',
                    render: (names: string[]) =>
                      names?.length ? names.map((n, i) => (
                        <Tag key={n} color={TAG_COLORS[i % TAG_COLORS.length]}>{n}</Tag>
                      )) : '—',
                  },
                ]}
              />
            )}

            {sectionCard('p-achievement', '专业成果', undefined,
              <SectionTable
                rows={profile.achievement}
                columns={[
                  { title: '成果名称', dataIndex: 'achievement_name' },
                  { title: '取得时间', dataIndex: 'obtain_time', render: dateStr },
                ]}
              />
            )}

            {sectionCard('p-language', '语言能力', undefined,
              <SectionTable
                rows={profile.language}
                columns={[
                  { title: '语种', dataIndex: 'language' },
                  { title: '熟练程度', dataIndex: 'proficiency' },
                  { title: '证书级别/分数', dataIndex: 'cert_level_or_score' },
                ]}
              />
            )}

            {sectionCard('p-contact', '通讯信息', undefined,
              <Descriptions column={2} size="small" bordered labelStyle={{ width: 120 }}>
                <Descriptions.Item label="手机号">{profile.contact?.mobile ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="办公电话">{profile.contact?.office_phone ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="家庭电话">{profile.contact?.home_phone ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="邮箱">{profile.contact?.email ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="家庭住址" span={2}>{profile.contact?.home_address ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="通勤时间">
                  {profile.contact?.commute_minutes != null ? `${profile.contact.commute_minutes} 分钟` : '—'}
                </Descriptions.Item>
              </Descriptions>
            )}

            {sectionCard('p-intent', '发展意向', undefined,
              profile.development_intent ? (
                <>
                  <Row gutter={[16, 10]}>
                    <Col span={12}><F label="职业发展方向" value={profile.development_intent.development_path} /></Col>
                    <Col span={12}><F label="轮岗意向" value={profile.development_intent.rotation_interest} /></Col>
                    <Col span={12}><F label="轮岗目标岗位" value={profile.development_intent.rotation_target} /></Col>
                    <Col span={12}><F label="学习课程" value={profile.development_intent.learning_courses} /></Col>
                  </Row>
                  <div style={{ borderTop: '1px dashed #f0f0f0', margin: '12px 0' }} />
                  <Row gutter={[16, 10]}>
                    <Col span={8}>
                      <Text type="secondary" style={{ fontSize: 12 }}>核心能力</Text>
                      <div style={{ marginTop: 6 }}>
                        {profile.development_intent.core_abilities.length
                          ? profile.development_intent.core_abilities.map((s, i) => (
                            <Tag key={s} color={TAG_COLORS[i % TAG_COLORS.length]}>{s}</Tag>
                          ))
                          : '—'}
                      </div>
                    </Col>
                    <Col span={8}>
                      <Text type="secondary" style={{ fontSize: 12 }}>能力提升方式</Text>
                      <div style={{ marginTop: 6 }}>
                        {profile.development_intent.learning_methods.length
                          ? profile.development_intent.learning_methods.map((s) => <Tag key={s}>{s}</Tag>)
                          : '—'}
                      </div>
                    </Col>
                    <Col span={8}>
                      <Text type="secondary" style={{ fontSize: 12 }}>实践机会意向</Text>
                      <div style={{ marginTop: 6 }}>
                        {profile.development_intent.project_interests.length
                          ? profile.development_intent.project_interests.map((s) => <Tag key={s}>{s}</Tag>)
                          : '—'}
                      </div>
                    </Col>
                  </Row>
                  <div style={{ borderTop: '1px dashed #f0f0f0', margin: '12px 0' }} />
                  <F label="短期目标" value={profile.development_intent.short_term_goal} />
                  <div style={{ marginTop: 8 }}><F label="中期目标" value={profile.development_intent.mid_term_goal} /></div>
                  <div style={{ marginTop: 8 }}><F label="其他补充" value={profile.development_intent.other_comments} /></div>
                </>
              ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
            )}
          </div>
        </Col>

        <Col flex="120px">
          <Anchor
            affix
            offsetTop={100}
            items={anchorItems.map((a) => ({ key: a.key, href: a.href, title: a.title }))}
          />
        </Col>
      </Row>
    </div>
  );
};

export default MyProfile;
