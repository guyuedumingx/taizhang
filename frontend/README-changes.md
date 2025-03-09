修改总结
1. 去除访客模式：修改 authStore.ts 中的 logout 函数，确保用户退出登录后直接显示登录界面。
2. 仪表盘使用真实 API：修改 Dashboard.tsx，使用真实 API 获取数据替代模拟数据。
3. 添加台账模板汇总功能：
   - 创建 TemplateLedgerSummary.tsx 组件显示特定模板的所有台账
   - 在 LedgerService.ts 添加获取特定模板台账的方法
   - 在 App.tsx 添加新的路由
   - 修改 TemplateList.tsx 添加查看台账汇总的按钮
