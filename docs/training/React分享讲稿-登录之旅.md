# React 分享讲稿：跟着一次登录，看懂整个项目

> 面向对象：前端完全新手 | 时长：45 分钟（30 分钟删减预案见文末）| 形式：live demo + 投屏看代码

## 开讲前检查清单（提前一天）

- [ ] 前后端本地跑通：后端 `uvicorn` + 前端 `cd frontend && npm run dev`
- [ ] 准备一个可登录的测试账号，登录一遍确认无故障
- [ ] VS Code 只打开 `frontend/src`，关闭其他标签页
- [ ] VS Code 字号调大（Cmd + + 调到现场最后一排能看清）
- [ ] 把本文档涉及的 4 个文件提前在 VS Code 里打开固定（见各节"投屏文件"）
- [ ] 浏览器开两个标签：登录页（未登录状态）、Dashboard（已登录状态）

**整场只投 4 个文件**（对新手，文件越少越好）：

| 文件 | 角色 |
|---|---|
| `src/pages/LoginPage.tsx` | 登录页：串起整个故事的枢纽 |
| `src/components/login/LoginForm.tsx` | 表单组件：讲组件/JSX/props |
| `src/stores/authStore.ts` | 全局状态：讲 state 与异步 |
| `src/App.tsx` | 路由表：讲页面跳转与守卫 |

---

## 第 0 节 开场（0:00-5:00，5 分钟）

### 演示动作
1. 投浏览器：登录页 → 输入账号 → 登录 → Dashboard（全程不说话，约 30 秒）
2. 切到 VS Code，全屏 `frontend/src` 目录树

### 口播要点
- "刚才那 30 秒，是一个 React 应用。今天 45 分钟不讲怎么写 React，讲一件事：**这个系统由什么组成、点一下登录按钮后代码里发生了什么**。听完你们不需要会写，但需要拿到一把钥匙——以后打开这个项目，知道往哪看。"
- "整个前端就一个目录 `frontend/src`，今天我们只看 4 个文件，讲完一次完整的登录。"
- TS 预防针（30 秒）："代码里有 `interface`、`string[]` 这类**类型标注**，是 TypeScript，相当于给代码写'说明书'。今天看到它们**直接当注释忽略**，不影响理解。"

---

## 第 1 节 起点：程序从哪开始跑（5:00-13:00，8 分钟）

### 投屏文件与行号
1. `src/main.tsx` 第 6-10 行（1 分钟即止）
2. `src/App.tsx` 第 84-124 行（路由表）

### 口播要点
- **main.tsx**："整个程序的入口只有一句话的意思：把 `<App />` 这棵组件树，塞进 HTML 里 id 叫 root 的那个空 div。从这行以后，都是 React 的世界。"（快速滚过，不恋战）
- **组件是什么**："React 里一切皆**组件**。组件 = 一个返回页面的函数。页面就是函数调用出来的，像搭积木。"
- **路由表**（App.tsx 84-124）："这是全项目的**地图**：左边是网址，右边是对应的页面组件。`/login` 对应 LoginPage，`/dashboard` 对应 Dashboard。想知道任何页面在哪，先来这张表查。"
- 指着第 101 行 `ledgers/edit/:id`："冒号是占位符，任意 id 都能匹配。"

### 心智模型一：UI = f(state)【正式讲，配箭头图】

```
   state（数据）                UI（页面）
   token: null      ──────▶    登录页
   token: "abc123"  ──────▶    工作台
        ▲                        │
        └────── 你只改数据 ───────┘
              页面自动变
```

- "**记住今天唯一一个公式：UI = f(state)，页面是数据的照片。**你不手动改页面，你只改数据，React 负责重新拍照。"
- **当场验证**：浏览器未登录标签页，手动把地址改成 `/dashboard` 回车 → 被弹回 `/login`。"为什么？因为数据（token）是空的，数据决定页面。这张照片此刻就该是登录页。"

---

## 第 2 节 表单：组件、JSX、props（13:00-21:00，8 分钟）

### 投屏文件与行号
`src/components/login/LoginForm.tsx` 全文（只有 66 行，放心通读）

### 口播要点
- **JSX**："第 16-63 行返回的东西叫 JSX——长得像 HTML 的 JavaScript。写 React 就是写 JSX。"
- **组件复用**："`LoginForm` 是个零件。注意第 15 行，它自己**不存任何数据**，是个'哑巴零件'——专业的活儿。"
- **props：父传子**：指着第 10-13 行
  ```ts
  interface LoginFormProps {
    onFinish: (values) => Promise<void>;   // 父组件塞进来的函数
    loading?: boolean;
  }
  ```
  "LoginPage 想用这个表单，就把'表单提交后干什么'（`onFinish` 函数）作为 **props** 传进来。**props 就是组件的入参**，函数传值、组件传 props，一回事。"

### 心智模型二：单向数据流【正式讲，配箭头图】

```
   LoginPage（父）                LoginForm（子）
   onLoginFinish 函数 ──props──▶  接住，挂到 Form 上
   （数据/函数只能向下传）
                                  用户点"登录"
   ◀──────── 调用 onFinish ────── （事件/调用向上反馈）
```

- "**数据像水，只能往下流**（父 → 子靠 props）；子组件想说话，只能**调用**父组件给的函数。这条规矩叫单向数据流，React 全项目的代码都遵守它。"
- 演示第 25-28 行的校验规则："EHR 号必须是 7 位数字——就写在这。以后产品说'改成 8 位'，你就知道来这改。"（**这就是 onboarding：让他们体验一次"找到改的地方"**）

---

## 第 3 节 提交：异步请求与全局状态（21:00-31:00，10 分钟）★全场核心

### 投屏文件与行号
1. `src/pages/LoginPage.tsx` 第 33-50 行（`onLoginFinish`）
2. `src/stores/authStore.ts` 第 37-81 行（`login` 函数）
3. `src/pages/LoginPage.tsx` 第 27-31 行（`useEffect` 监听）
4. `src/stores/authStore.ts` 第 151-159 行（persist）

### 口播要点
- **接力**："LoginForm 调了 `onFinish`，实际就是 LoginPage 第 33 行的 `onLoginFinish`。看，箭头图活了。"
- **异步**："`await login(...)`——网络请求要等服务器回话，所以有 await。就像点外卖：下单后你不会盯着手机不动，页面也不会卡死。"
- **authStore.login（37-81 行）逐段看**：
  - 39-48 行：发请求（先忽略细节）
  - 58-71 行：**全场最重要的一屏**——`set({ token, isAuthenticated: true, ... })`
    "拿到 token 后只做一件事：**改数据**。还记得公式吗？UI = f(state)。数据一变，马上看第三次验证。"
- **useEffect 自动跳转**（LoginPage 27-31 行）：
  ```ts
  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard');
  }, [isAuthenticated]);
  ```
  "这段像装了个'监控器'：盯着 `isAuthenticated`，它一变 true，自动跳工作台。**没有任何代码写着'手动把登录页换成工作台'**——数据变了，页面自己换。这就是 React 和 jQuery 时代最大的区别。"
- **persist（151-159 行，30 秒）**："刷新页面为什么不用重新登录？zustand 的 persist 把这几个字段自动存进了浏览器 localStorage。"（演示：F12 → Application → Local Storage → auth-storage）

### 心智模型一验证清单（带大家回顾）
| 时刻 | 数据变化 | 页面自动变化 |
|---|---|---|
| 未登录访问 /dashboard | token = null | 弹回登录页 |
| 登录成功 | isAuthenticated = true | 跳转工作台 |
| 退出登录 | token = null（authStore 83-94 行） | 回到登录页 |

---

## 第 4 节 守卫与全景地图（31:00-40:00，9 分钟）

### 投屏文件与行号
1. `src/App.tsx` 第 33-36 行（`PrivateRoute`）
2. `src/App.tsx` 第 92-98 行（Layout 嵌套路由，快过）
3. VS Code 目录树（收尾全景）

### 口播要点
- **PrivateRoute 全文只有 3 行**：
  ```tsx
  function PrivateRoute({ children }) {
    const { isAuthenticated } = useAuthStore();
    return isAuthenticated ? children : <Navigate to="/login" />;
  }
  ```
  "登录守卫就这么点：已登录显示页面，没登录 `Navigate` 踢回登录页。条件渲染就是 JavaScript 的三元表达式。"
- "为什么它有权限读全局登录态？第 34 行 `useAuthStore()`——任何组件、任何层级，一行就能拿到全局状态，不用一层层传 props。**这就是为什么登录信息放 zustand 全局 store，而不放某个组件里**。"
- **目录地图**（投目录树，每层一句话）：
  ```
  src/
  ├── main.tsx        入口：把 App 挂到 HTML 上
  ├── App.tsx         路由表：网址 ↔ 页面对照表 + 登录守卫
  ├── pages/          页面组件（每个网址对应一个文件）
  ├── components/     可复用零件（登录表单、布局、弹窗…）
  ├── stores/         全局状态（登录态、权限—— zustand）
  ├── contexts/       另一种跨组件共享（面包屑导航）
  ├── hooks/          自定义 Hook（可复用的状态逻辑）
  ├── api/            和后端说话的地方（所有网络请求）
  ├── services/       对 api 的业务封装
  └── utils/          纯工具函数
  ```
- 留钩子："权限控制 `hasPermission`（authStore 96-105 行）、面包屑、拖拽排序，都是这套基础的变体，下次专题讲。"

---

## 第 5 节 收尾（40:00-45:00，5 分钟）

- 发速查表（`docs/training/新人速查表-想改X去哪找.md`）："会后只需要记住两个心智模型 + 这张表。"
- **课后小任务**（1 分钟可完成）："产品要求 EHR 号从 7 位改成 8 位，去哪改？"（答案：LoginForm.tsx 第 27 行正则）——检验他们是否建立了"需求 → 定位文件"的反射
- Q&A

---

## 30 分钟删减预案

时间不够时**按序砍**（砍一条讲一条，不要每节都挤一点）：

| 序 | 砍什么 | 省 | 影响 |
|---|---|---|---|
| 1 | 第 1 节 main.tsx 不讲，开场直接说"入口把 App 挂到网页上" | -3 min | 无（新手不需要入口细节） |
| 2 | 第 3 节 persist/localStorage 演示，改成一句话 | -2 min | 小 |
| 3 | 第 4 节 Layout 嵌套路由 + hasPermission 钩子 | -3 min | 小（本就是预告性质） |
| 4 | 第 4 节目录地图只讲 pages/components/stores/api 四层 | -2 min | 中（速查表可补） |
| 5 | 第 5 节课后小任务改为"回去自己试试" | -3 min | 中 |
| — | **以上全砍后约 32 分钟**；再不够砍第 2 节的校验规则演示（-2 min） | | |

**绝不砍的三样**：两个心智模型的箭头图、authStore 的 `set()` 与 useEffect 联动（第 3 节核心）、PrivateRoute 三行守卫——它们是"看懂这个项目"的最低配置。
