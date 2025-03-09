# 台账管理系统

台账管理系统是一个专为企业设计的综合性台账数据管理平台，旨在帮助企业高效管理各类台账数据，提升数据管理效率，降低管理成本。系统支持多用户、多角色、多团队协作，具备完善的权限控制机制，确保数据安全可靠。

## 功能特点

- **台账管理**：创建、编辑、查询和导出台账数据
- **模板管理**：自定义台账模板，灵活配置字段
- **用户管理**：管理系统用户，分配角色和权限
- **角色管理**：创建和管理角色，配置权限
- **团队管理**：创建和管理团队，分配用户
- **权限控制**：细粒度的权限控制，保障数据安全

## 技术栈

### 后端

- **语言**：Python 3.11+
- **Web框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：PostgreSQL
- **身份认证**：JWT (JSON Web Tokens)
- **权限管理**：Casbin

### 前端

- **语言**：TypeScript
- **框架**：React 18
- **UI组件库**：Ant Design 5
- **状态管理**：Zustand
- **路由**：React Router
- **HTTP客户端**：Axios
- **构建工具**：Vite

## 快速开始

### 系统要求

- **操作系统**：Windows 10+、macOS 10.15+、Linux (Ubuntu 20.04+)
- **Python**：3.11+
- **Node.js**：18.0+
- **PostgreSQL**：14.0+
- **Git**：2.30+

### 安装步骤

1. 克隆代码仓库

```bash
git clone https://github.com/yourusername/taizhang.git
cd taizhang
```

2. 后端设置

```bash
# 创建并激活虚拟环境
python -m venv backend/venv
source backend/venv/bin/activate  # 在Windows上使用 backend\venv\Scripts\activate

# 安装依赖
cd backend
pip install -r requirements.txt

# 配置环境变量
# 创建.env文件并添加必要的配置

# 初始化数据库
alembic upgrade head

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 前端设置

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm run dev
```

4. 访问应用

打开浏览器，访问 http://localhost:5173

## 文档

详细的文档可以在 `docs` 目录中找到：

- [用户手册](docs/user/README.md)
- [开发者文档](docs/developer/README.md)

## 贡献

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

- 项目维护者：Your Name
- 电子邮件：your.email@example.com

## 更新日志

### 2023-11-20 用户数据模型更新
- 移除了User模型中的所有Email字段
- 添加了EHR_ID字段作为用户唯一标识符
- 更新了所有相关的API端点和测试
- 所有测试用例通过

### 2023-11-22 前端路由修复
- 修复了工作流管理模块的路由问题，确保正确导航到/workflow相关页面
- 修复了台账管理模块的路由问题，确保正确导航到/ledgers相关页面
- 统一了前端路由路径，避免使用不一致的路径格式
- 修复了LedgerForm和WorkflowForm组件中的类型问题和路由跳转逻辑
- 优化了组件中的条件渲染，提高了用户体验 