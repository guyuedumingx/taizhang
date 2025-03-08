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
│   │   │   ├── endpoints/   # API端点
│   │   │   └── api.py       # API路由
│   │   └── deps.py          # 依赖注入
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置
│   │   ├── security.py      # 安全相关
│   │   └── settings.py      # 应用设置
│   ├── db/                  # 数据库相关
│   │   ├── base.py          # 基础模型
│   │   ├── base_class.py    # 基类
│   │   └── session.py       # 数据库会话
│   ├── models/              # 数据模型
│   │   ├── user.py          # 用户模型
│   │   ├── team.py          # 团队模型
│   │   ├── role.py          # 角色模型
│   │   ├── ledger.py        # 台账模型
│   │   ├── template.py      # 模板模型
│   │   └── field.py         # 字段模型
│   ├── schemas/             # Pydantic模型
│   │   ├── user.py          # 用户模式
│   │   ├── team.py          # 团队模式
│   │   ├── role.py          # 角色模式
│   │   ├── ledger.py        # 台账模式
│   │   ├── template.py      # 模板模式
│   │   └── token.py         # 令牌模式
│   ├── services/            # 业务服务
│   │   ├── user.py          # 用户服务
│   │   ├── auth.py          # 认证服务
│   │   ├── casbin.py        # 权限服务
│   │   └── ledger.py        # 台账服务
│   ├── utils/               # 工具函数
│   │   └── security.py      # 安全工具
│   └── main.py              # 应用入口
├── tests/                   # 测试代码
│   ├── api/                 # API测试
│   ├── services/            # 服务测试
│   └── conftest.py          # 测试配置
├── .env                     # 环境变量
├── requirements.txt         # 依赖列表
└── pyproject.toml           # 项目配置
```

## 前端结构

前端采用React + TypeScript，代码组织如下：

```
frontend/
├── public/                  # 静态资源
│   ├── favicon.ico          # 网站图标
│   └── index.html           # HTML模板
├── src/                     # 源代码
│   ├── api/                 # API请求
│   │   ├── auth.ts          # 认证API
│   │   ├── user.ts          # 用户API
│   │   ├── team.ts          # 团队API
│   │   ├── role.ts          # 角色API
│   │   ├── ledger.ts        # 台账API
│   │   └── template.ts      # 模板API
│   ├── components/          # 组件
│   │   ├── Layout.tsx       # 布局组件
│   │   ├── Sidebar.tsx      # 侧边栏组件
│   │   └── ...              # 其他组件
│   ├── config/              # 配置
│   │   ├── api.ts           # API配置
│   │   └── index.ts         # 全局配置
│   ├── pages/               # 页面
│   │   ├── LoginPage.tsx    # 登录页
│   │   ├── Dashboard.tsx    # 首页
│   │   ├── admin/           # 管理页面
│   │   ├── ledger/          # 台账页面
│   │   └── template/        # 模板页面
│   ├── stores/              # 状态管理
│   │   ├── authStore.ts     # 认证状态
│   │   └── ...              # 其他状态
│   ├── types/               # 类型定义
│   │   ├── user.ts          # 用户类型
│   │   └── ...              # 其他类型
│   ├── utils/               # 工具函数
│   │   ├── request.ts       # 请求工具
│   │   └── ...              # 其他工具
│   ├── App.css              # 全局样式
│   ├── App.tsx              # 应用入口
│   ├── index.css            # 入口样式
│   └── main.tsx             # 入口文件
├── .eslintrc.json           # ESLint配置
├── package.json             # 依赖配置
├── tsconfig.json            # TypeScript配置
└── vite.config.ts           # Vite配置
```

## 文档结构

项目文档组织如下：

```
docs/
├── user/                    # 用户文档
│   └── README.md            # 用户手册
├── developer/               # 开发者文档
│   ├── README.md            # 开发者手册
│   ├── environment.md       # 环境搭建
│   ├── structure.md         # 项目结构
│   ├── backend.md           # 后端开发
│   ├── frontend.md          # 前端开发
│   ├── database.md          # 数据库设计
│   ├── api.md               # API文档
│   └── deployment.md        # 部署指南
└── images/                  # 文档图片
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
- **src/utils/request.ts**: HTTP请求工具，基于Axios封装
- **src/api/**: API请求定义，包含所有后端API的调用方法 