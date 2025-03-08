# 开发环境搭建

本文档将指导您如何搭建台账管理系统的开发环境。

## 系统要求

- **操作系统**：Windows 10+、macOS 10.15+、Linux (Ubuntu 20.04+)
- **Python**：3.11+
- **Node.js**：18.0+
- **PostgreSQL**：14.0+
- **Git**：2.30+

## 后端环境搭建

### 1. 克隆代码仓库

```bash
git clone https://github.com/yourusername/taizhang.git
cd taizhang
```

### 2. 创建并激活虚拟环境

```bash
# 在Windows上
python -m venv backend/venv
backend\venv\Scripts\activate

# 在macOS/Linux上
python -m venv backend/venv
source backend/venv/bin/activate
```

### 3. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 配置环境变量

创建`.env`文件：

```bash
# 在backend目录下
touch .env  # 在Windows上使用 type nul > .env
```

编辑`.env`文件，添加以下内容：

```
# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=taizhang

# 安全配置
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 跨域配置
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# 其他配置
PROJECT_NAME=台账管理系统
API_V1_STR=/api/v1
```

### 5. 初始化数据库

```bash
# 确保PostgreSQL服务已启动
# 创建数据库
createdb taizhang

# 运行数据库迁移
alembic upgrade head
```

### 6. 启动后端服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

现在，后端API服务应该已经在`http://localhost:8000`上运行。

## 前端环境搭建

### 1. 安装依赖

```bash
cd frontend
npm install
# 或者使用pnpm
# pnpm install
```

### 2. 配置环境变量

创建`.env.local`文件：

```bash
# 在frontend目录下
touch .env.local  # 在Windows上使用 type nul > .env.local
```

编辑`.env.local`文件，添加以下内容：

```
VITE_API_URL=http://localhost:8000/api/v1
```

### 3. 启动开发服务器

```bash
npm run dev
# 或者使用pnpm
# pnpm dev
```

现在，前端开发服务器应该已经在`http://localhost:5173`上运行。

## 数据库设置

### 安装PostgreSQL

#### Windows

1. 下载并安装[PostgreSQL](https://www.postgresql.org/download/windows/)
2. 安装过程中设置用户名和密码
3. 安装完成后，使用pgAdmin或psql创建数据库

#### macOS

使用Homebrew安装：

```bash
brew install postgresql
brew services start postgresql
```

#### Linux (Ubuntu)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 创建数据库

```bash
# 登录PostgreSQL
sudo -u postgres psql

# 创建数据库
CREATE DATABASE taizhang;

# 创建用户（如果需要）
CREATE USER taizhang_user WITH PASSWORD 'password';

# 授权
GRANT ALL PRIVILEGES ON DATABASE taizhang TO taizhang_user;

# 退出
\q
```

## 验证环境

### 验证后端

访问`http://localhost:8000/docs`，应该能看到Swagger UI文档界面。

### 验证前端

访问`http://localhost:5173`，应该能看到系统登录界面。

## 常见问题

### 后端启动问题

**Q: 启动后端服务时报"Address already in use"错误**

A: 端口8000已被占用，可以使用不同的端口：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Q: 数据库连接失败**

A: 检查PostgreSQL服务是否启动，以及`.env`文件中的数据库配置是否正确。

### 前端启动问题

**Q: 安装依赖时报错**

A: 尝试清除npm缓存后重新安装：

```bash
npm cache clean --force
npm install
```

**Q: 前端无法连接到后端API**

A: 检查`.env.local`文件中的API URL配置，以及后端服务是否正常运行。确保CORS配置正确。 