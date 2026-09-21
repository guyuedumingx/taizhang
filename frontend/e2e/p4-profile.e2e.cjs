/**
 * P4 第一批（我的档案读路径）E2E + API 测试
 * 运行前提: backend :8080, frontend :5173 已启动; dev 库已种子化
 *   admin/0000001/admin123(超管), zhangsan/1000001/zhangsan123(测试一组)
 * 运行: cd frontend/e2e && node p4-profile.e2e.js
 * 依赖: npm i playwright（或复用全局缓存）
 */
const { chromium } = require('playwright');

const BASE = 'http://localhost:5173';
const API = 'http://localhost:8080/api/v1';
const results = [];
let ctxId = '';

async function test(id, name, fn) {
  try {
    await fn();
    results.push({ id, name, pass: true });
    console.log(`PASS ${id} ${name}`);
  } catch (e) {
    results.push({ id, name, pass: false, detail: String(e).slice(0, 200) });
    console.log(`FAIL ${id} ${name} :: ${String(e).slice(0, 160)}`);
  }
}
const expect = (cond, msg) => { if (!cond) throw new Error(msg || '断言失败'); };

async function apiLogin(ehr, password) {
  const r = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `username=${ehr}&password=${password}`,
  });
  const j = await r.json();
  if (!j.access_token) throw new Error(`登录失败 ${ehr}: ${JSON.stringify(j)}`);
  return j.access_token;
}

(async () => {
  // ================= A. API 接口层 =================
  const zhangTok = await apiLogin('1000001', 'zhangsan123');
  const adminTok = await apiLogin('0000001', 'admin123');
  const HZ = { Authorization: `Bearer ${zhangTok}` };
  const HA = { Authorization: `Bearer ${adminTok}` };

  await test('A1', '无 token 访问 /me 返回 401', async () => {
    const r = await fetch(`${API}/portrait/profiles/me`);
    expect(r.status === 401, `status=${r.status}`);
  });

  await test('A2', '本人 GET /me 返回 200 且结构完整、数据正确', async () => {
    const r = await fetch(`${API}/portrait/profiles/me`, { headers: HZ });
    expect(r.status === 200, `status=${r.status}`);
    const j = await r.json();
    expect(j.name === '张三' && j.ehr_no === '1000001' && j.group_name === '测试一组', '基础字段不符');
    expect(j.base && j.base.gender === '男' && j.base.nation === '汉族', 'base 不符');
    for (const k of ['political','education','family','resume','reward','qualification','achievement','language','skill_tags','project_summaries'])
      expect(Array.isArray(j[k]), `${k} 非数组`);
    expect(j.contact && j.contact.mobile === '13800000000', 'contact 不符');
    expect(j.development_intent && Array.isArray(j.development_intent.core_abilities), '发展意向不符');
    expect(j.political[0]?.political_status === '中共党员', '政治面貌不符');
  });

  await test('A3', '管理员首次 GET /me 自动建档', async () => {
    const r1 = await fetch(`${API}/portrait/profiles/me`, { headers: HA });
    const j = await r1.json();
    expect(r1.status === 200 && j.base !== undefined, '未返回 base 结构');
  });

  await test('A4', '本人读他人档案（无组权限）返回 403', async () => {
    const r = await fetch(`${API}/portrait/profiles/by-ehr/0000001`, { headers: HZ });
    expect(r.status === 403, `status=${r.status}`);
  });

  await test('A5', '超管读他人档案返回 200', async () => {
    const r = await fetch(`${API}/portrait/profiles/by-ehr/1000001`, { headers: HA });
    expect(r.status === 200, `status=${r.status}`);
    const j = await r.json();
    expect(j.name === '张三', '返回的不是张三的档案');
  });

  await test('A6', '读取不存在用户返回 404', async () => {
    const r = await fetch(`${API}/portrait/profiles/by-ehr/9999999`, { headers: HA });
    expect(r.status === 404, `status=${r.status}`);
  });

  // 组范围语义: 造 同组leader(可看) / 同组无权user(403) / 异组leader(403)
  {
    const { execSync } = require('child_process');
    execSync('./venv/bin/python ../frontend/e2e/seed_group_users.py', {
      cwd: '/Users/zhuojialin/projects/collab/taizhang/backend',
      stdio: 'pipe',
    });
  }

  await test('A7', '同组 leader（portrait_group:read + 同部门）可看组员档案 → 200', async () => {
    const tok = await apiLogin('1000002', 'test1234');
    const r = await fetch(`${API}/portrait/profiles/by-ehr/1000001`, { headers: { Authorization: `Bearer ${tok}` } });
    expect(r.status === 200, `status=${r.status}`);
  });

  await test('A8', '同组普通 user（无 portrait_group 权限）看组员 → 403', async () => {
    const tok = await apiLogin('2000001', 'test1234');
    const r = await fetch(`${API}/portrait/profiles/by-ehr/1000001`, { headers: { Authorization: `Bearer ${tok}` } });
    expect(r.status === 403, `status=${r.status}`);
  });

  await test('A9', '异组 leader（有权限但部门不同）看档案 → 403', async () => {
    const tok = await apiLogin('2000002', 'test1234');
    const r = await fetch(`${API}/portrait/profiles/by-ehr/1000001`, { headers: { Authorization: `Bearer ${tok}` } });
    expect(r.status === 403, `status=${r.status}`);
  });

  // ================= B. 浏览器 E2E =================
  const browser = await chromium.launch({ headless: true });

  await test('B1', '错误密码登录被拒并提示', async () => {
    const page = await (await browser.newContext()).newPage();
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await page.locator('input:visible').first().fill('1000001');
    await page.locator('input[type="password"]').fill('wrong-password');
    await page.locator('button[type="submit"], button:has-text("登录")').first().click();
    await page.waitForTimeout(1200);
    const text = await page.locator('body').innerText();
    expect(text.includes('EHR号或密码错误') || (await page.locator('.ant-message, .ant-form-item-explain-error').count()) > 0, '未见错误提示');
    expect(!page.url().includes('/dashboard'), '不应进入系统');
    await page.context().close();
  });

  await test('B5', '未登录访问档案页跳转 /login', async () => {
    const page = await (await browser.newContext()).newPage();
    await page.goto(`${BASE}/dashboard/portrait/profile`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);
    expect(page.url().includes('/login'), `url=${page.url()}`);
    await page.context().close();
  });

  // 张三完整浏览会话
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e)));

  await test('B2', '正确凭据登录进入仪表盘', async () => {
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await page.locator('input:visible').first().fill('1000001');
    await page.locator('input[type="password"]').fill('zhangsan123');
    await page.locator('button[type="submit"], button:has-text("登录")').first().click();
    await page.waitForURL('**/dashboard**', { timeout: 15000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    expect(page.url().includes('/dashboard'), `url=${page.url()}`);
  });

  await test('B19', '回归：仪表盘统计渲染正常', async () => {
    const text = await page.locator('body').innerText();
    expect(text.includes('系统概览') && text.includes('台账总数'), '仪表盘内容缺失');
  });

  await test('B3', '侧边栏存在"数字画像"分组', async () => {
    const t = await page.locator('.ant-layout-sider').innerText();
    expect(t.includes('数字画像'), '分组缺失');
  });

  await test('B4', '子菜单 7 项：我的档案可用、其余 6 项禁用', async () => {
    await page.locator('.ant-menu-submenu:has-text("数字画像") .ant-menu-submenu-title').click();
    await page.waitForTimeout(400);
    const items = ['我的档案', '家访记录', '档案管理', '智能筛选', '能力分析', '组员调换', '技能标签'];
    for (const it of items) expect((await page.locator(`.ant-menu-sub li:has-text("${it}")`).count()) >= 1, `缺少 ${it}`);
    const disabledCount = await page.locator('.ant-menu-sub li.ant-menu-item-disabled').count();
    expect(disabledCount === 6, `禁用项=${disabledCount}`);
    const enabledProfile = await page.locator('.ant-menu-sub li:has-text("我的档案")').getAttribute('class');
    expect(!enabledProfile.includes('disabled'), '我的档案不应禁用');
  });

  await test('B6', '档案页面包屑与标题正确', async () => {
    await page.goto(`${BASE}/dashboard/portrait/profile`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    const text = await page.locator('body').innerText();
    expect(text.includes('数字画像') && text.includes('我的档案'), '面包屑/标题缺失');
    expect((await page.locator('h4:has-text("我的档案")').count()) === 1, '页标题缺失');
  });

  await test('B7', '13 个区块齐全 + 右侧锚点 13 项', async () => {
    const sections = ['基础信息','技能标签','政治面貌','学历学位','家庭关系','简历','奖惩信息','资格证书','项目总结','专业成果','语言能力','通讯信息','发展意向'];
    const text = await page.locator('body').innerText();
    for (const s of sections) expect(text.includes(s), `缺少区块 ${s}`);
    expect((await page.locator('.ant-anchor-link').count()) === 13, '锚点数不为 13');
  });

  await test('B8', '基础信息数据正确', async () => {
    const text = await page.locator('#p-base').innerText();
    for (const s of ['张三', '1000001', '测试一组', '男', '汉族', '1995-06-15', '数据分析岗', '浙江杭州']) expect(text.includes(s), `缺 ${s}`);
  });

  await test('B9', '应急先锋队徽章显示', async () => {
    expect((await page.locator('#p-base .ant-tag:has-text("应急先锋队")').count()) === 1, '徽章缺失');
  });

  await test('B10', '技能标签显示 2 个', async () => {
    const tags = await page.locator('#p-tags .ant-tag').allInnerTexts();
    expect(tags.includes('Python') && tags.includes('数据分析') && tags.length === 2, `tags=${tags}`);
  });

  await test('B11', '政治面貌表格数据', async () => {
    const t = await page.locator('#p-political').innerText();
    expect(t.includes('中共党员') && t.includes('2016-06-20'), `内容不符: ${t.slice(0, 80)}`);
  });

  await test('B12', '学历学位表格数据', async () => {
    const t = await page.locator('#p-education').innerText();
    expect(t.includes('硕士研究生') && t.includes('工学硕士') && t.includes('计算机技术'), '内容不符');
  });

  await test('B13', '7 个无数据区块显示"暂无数据"', async () => {
    const emptyIds = ['p-family','p-resume','p-reward','p-qualification','p-projects','p-achievement','p-language'];
    for (const id of emptyIds) {
      const n = await page.locator(`#${id} .ant-empty`).count();
      expect(n >= 1, `${id} 无空态`);
    }
  });

  await test('B14', '通讯信息数据', async () => {
    const t = await page.locator('#p-contact').innerText();
    expect(t.includes('13800000000') && t.includes('zhangsan@example.com') && t.includes('20 分钟'), '内容不符');
  });

  await test('B15', '发展意向数据与标签', async () => {
    const t = await page.locator('#p-intent').innerText();
    expect(t.includes('数据分析方向') && t.includes('机器学习') && t.includes('数据可视化') && t.includes('独立负责数据分析项目'), '内容不符');
  });

  await test('B16', '点击右侧锚点跳转到对应区块', async () => {
    await page.locator('.ant-anchor-link-title:has-text("发展意向")').click();
    await page.waitForTimeout(2000);
    expect(page.url().includes('p-intent'), `hash=${page.url()}`);
    const box = await page.locator('#p-intent').boundingBox();
    // 区块进入视口即算滚动成功（末尾区块受页面最大滚动限制, 无法贴到顶部）
    expect(box && box.y >= 0 && box.y < 900, `区块未进入视口 y=${box?.y}`);
  });

  await test('B17', 'admin 查看（空档案）页面正常、自动建档', async () => {
    const page2 = await (await browser.newContext()).newPage();
    const e2 = [];
    page2.on('pageerror', (e) => e2.push(String(e)));
    await page2.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await page2.locator('input:visible').first().fill('0000001');
    await page2.locator('input[type="password"]').fill('admin123');
    await page2.locator('button[type="submit"], button:has-text("登录")').first().click();
    await page2.waitForURL('**/dashboard**', { timeout: 15000 });
    await page2.goto(`${BASE}/dashboard/portrait/profile`, { waitUntil: 'networkidle' });
    await page2.waitForTimeout(1000);
    const text = await page2.locator('body').innerText();
    expect(text.includes('系统管理员') && text.includes('0000001'), '基础信息不符');
    expect((await page2.locator('.ant-empty').count()) >= 10, '空态数量异常');
    expect(e2.length === 0, `JS错误: ${e2[0]}`);
    await page2.context().close();
  });

  await test('B18', '张三会话全程无 JS 错误', async () => {
    expect(pageErrors.length === 0, pageErrors[0] || '');
  });

  await page.screenshot({ path: '/tmp/p4_e2e/final_zhangsan.png', fullPage: true });
  await browser.close();

  // ================= 汇总 =================
  const pass = results.filter((r) => r.pass).length;
  console.log(`\n===== 结果: ${pass}/${results.length} 通过 =====`);
  const failed = results.filter((r) => !r.pass);
  if (failed.length) {
    console.log('失败清单:');
    failed.forEach((f) => console.log(`  ${f.id} ${f.name} :: ${f.detail}`));
  }
  process.exit(0);
})();
