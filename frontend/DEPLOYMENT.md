按照我们的修改，已完成如下功能:

1. 去除访客模式 - 修改了authStore.ts
2. 仪表盘使用真实API - 修改了Dashboard.tsx
3. 创建了台账模板汇总页面 - TemplateLedgerSummary.tsx
4. 修改了moment为dayjs - 解决了依赖问题

请在启动项目前，确保执行:
```
npm install --save dayjs
```

然后可以启动项目测试:
```
npm run dev
```
