# 台账系统前端速查表：想改 X，去哪找

> 配套分享：《React 分享讲稿-登录之旅》。会后记不住代码没关系，记住这张表。

## 两个心智模型（全场就这两个知识点）

```
① UI = f(state)                 ② 单向数据流
   数据变了，页面自动变             父 --props--> 子
   你只改数据，不手动改页面         子 --调用父给的函数--> 父
```

## 需求 → 文件 对照表

| 需求/想改什么 | 去哪个文件 |
|---|---|
| 任何页面"在哪个网址" / 新增页面 | `src/App.tsx`（路由表，第 84 行起） |
| 登录表单（EHR 号校验、密码规则） | `src/components/login/LoginForm.tsx` |
| 登录成功后做什么 | `src/pages/LoginPage.tsx`（`onLoginFinish`，第 33 行） |
| 退出登录 / 权限判断 | `src/stores/authStore.ts`（`logout` 第 83 行 / `hasPermission` 第 96 行） |
| 顶部菜单、整体布局 | `src/components/Layout.tsx` |
| 面包屑导航 | `src/contexts/NavigationContext.tsx` + `src/components/common/BreadcrumbNav.tsx` |
| 台账列表（表格列、筛选） | `src/pages/ledger/LedgerList.tsx` |
| 台账新增/编辑表单 | `src/pages/ledger/LedgerForm.tsx` |
| 模板管理 | `src/pages/template/TemplateForm.tsx`（含拖拽排序 dnd-kit，进阶） |
| 某个接口的地址/参数 | `src/api/` 对应文件（按模块命名，如 `ledgers.ts`） |
| 主题色、按钮颜色 | `src/App.tsx`（ConfigProvider，第 40 行起） |
| 页面文字、文案 | 先全局搜索那句话（VS Code: Cmd+Shift+F） |

## 目录一句话版

```
src/
├── main.tsx      入口（把 App 挂到网页上，基本不用动）
├── App.tsx       路由表 + 登录守卫
├── pages/        页面（每个网址一个文件）
├── components/   可复用零件（表单、弹窗、布局…）
├── stores/       全局状态（登录态、台账列表—— zustand）
├── contexts/     跨组件共享（面包屑）
├── hooks/        可复用状态逻辑
├── api/          所有网络请求
├── services/     api 的业务封装
└── utils/        工具函数
```

## 排查三步法（改不动/找不到时）

1. **找页面**：看浏览器地址栏 URL → 去 `App.tsx` 路由表查对应组件
2. **找数据**：页面里内容从哪来 → 看该文件顶部的 import（api？store？props？）
3. **找文案**：全局搜索（Cmd+Shift+F）那句话本身

## 常见"为什么"

| 疑问 | 一句话答案 |
|---|---|
| 为什么刷新后还登录着？ | 登录态存在浏览器 localStorage（zustand persist） |
| 为什么组件里改界面要先 setState/set？ | UI = f(state)，改数据 React 才知道要重新渲染 |
| `interface` / `: string` 是什么？ | TypeScript 类型标注，先当注释忽略 |
| 页面怎么相互跳转？ | `navigate('/xxx')`，配合 App.tsx 路由表 |
| 为什么组件文件名大写开头？ | React 规定：小写会被当成 HTML 标签 |
