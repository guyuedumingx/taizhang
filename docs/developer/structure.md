# 项目结构

本文档介绍台账管理系统的项目结构，帮助开发者快速了解代码组织方式。

## 整体结构

项目采用前后端分离的结构，主要分为以下几个部分：

```
taizhang/
├── backend/         # 后端代码
├── frontend/        # 前端代码
├── docs/            # 项目文档
├── .gitignore       # Git忽略文件
└── README.md        # 项目说明
```

## 后端结构

后端采用FastAPI框架，代码组织如下：

```
backend/
├── alembic/                 # 数据库迁移相关
│   ├── versions/            # 迁移版本
│   ├── env.py               # 迁移环境配置
│   └── alembic.ini          # Alembic配置文件
├── app/                     # 应用代码
│   ├── api/                 # API相关
│   │   ├── api_v1/          # API v1版本
│   │   │   ├── endpoints/   # 各业务域路由
│   │   │   └── api.py       # API 路由聚合
│   │   └── deps.py          # 依赖注入
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置，读取 .env（支持 Oracle/SQLite）
│   │   ├── security.py      # JWT、密码哈希
│   │   ├── rbac_model.conf  # Casbin 模型
│   │   └── policy.csv       # Casbin 示例策略
│   ├── db/                  # 数据库相关
│   │   ├── base.py          # Base 注册
│   │   ├── session.py       # SQLAlchemy Engine / Session（含 Oracle 优化）
│   │   ├── init_db.py       # 初始化角色、权限、超级用户
│   │   └── insert_test_data.py # 可选测试数据脚本
│   ├── models/              # SQLAlchemy 数据模型
│   ├── schemas/             # Pydantic 模型
│   ├── services/            # 业务服务层（auth_service、ledger_service 等）
│   ├── utils/               # 工具函数（logger、通用工具）
│   └── main.py              # FastAPI 应用入口
├── tests/                   # 测试代码（API / 服务 / 数据库）
│   └── ...                  # pytest 测试用例与配置
├── requirements.txt         # Python 依赖
├── main.py                  # 直接运行后端的入口（加载 app.main）
├── init_db.py               # 便捷初始化脚本
└── create_test_user.py      # 创建测试用户脚本
```

## 前端结构

前端采用React + TypeScript，代码组织如下：

```
frontend/
├── public/                  # 静态资源
│   ├── favicon.ico          # 网站图标
│   └── index.html           # HTML模板
├── src/                     # 源代码
│   ├── api/                 # API 请求封装（auth、users、ledgers、workflows 等）
│   ├── components/          # 组件
│   │   ├── Layout.tsx       # 布局组件
│   │   ├── Sidebar.tsx      # 侧边栏组件
│   │   └── ...              # 其他组件
│   ├── config.ts            # 前端全局配置（API 基础地址、权限常量）
│   ├── pages/               # 页面
│   │   ├── LoginPage.tsx    # 登录页
│   │   ├── Dashboard.tsx    # 首页
│   │   ├── admin/           # 管理页面
│   │   ├── ledger/          # 台账页面
│   │   └── template/        # 模板页面
│   ├── stores/              # 状态管理（authStore.ts）
│   ├── types.ts             # 全局类型定义
│   ├── utils/               # 工具函数（导出、权限分组等）
│   ├── App.css / index.css  # 全局样式
│   ├── App.tsx              # 路由配置
│   └── main.tsx             # 程序入口
├── eslint.config.js         # ESLint配置
├── package.json             # 依赖配置
├── tsconfig.json            # TypeScript基础配置
├── tsconfig.app.json        # 前端编译配置
├── tsconfig.node.json       # Node 构建配置
└── vite.config.ts           # Vite配置
```

## 文档结构

项目文档组织如下：

```
docs/
├── user/                    # 用户文档
│   └── README.md            # 用户手册
├── developer/               # 开发者文档
│   ├── README.md            # 开发说明（概览、技术栈）
│   ├── environment.md       # 环境搭建指南
│   └── structure.md         # 项目结构说明
└── mermaid/                 # 架构/流程图（Mermaid）
```

## 关键文件说明

### 后端关键文件

- **app/main.py**: 应用入口，包含FastAPI实例创建和中间件配置
- **app/core/config.py**: 应用配置，包含环境变量读取和配置项
- **app/api/api_v1/api.py**: API路由注册，包含所有API端点的路由
- **app/db/base.py**: 数据库模型导入，用于Alembic自动检测模型变更
- **app/models/**: 数据库模型定义，使用SQLAlchemy ORM
- **app/schemas/**: 数据验证和序列化模型，使用Pydantic
- **app/services/**: 业务逻辑服务，包含核心业务功能实现

### 前端关键文件

- **src/main.tsx**: 应用入口，包含React渲染和路由配置
- **src/App.tsx**: 应用组件，包含路由定义和全局配置
- **src/components/Layout.tsx**: 布局组件，定义应用整体布局
- **src/stores/authStore.ts**: 认证状态管理，使用Zustand
- **src/api/index.ts**: Axios 实例与各业务 API 聚合
- **src/utils/exportUtils.ts**: 前端导出工具函数
- **src/config.ts**: 全局配置与权限常量