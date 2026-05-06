# Seele 股票数据管理后端

基于 FastAPI + SQLAlchemy 的股票数据管理后端服务。

## 技术栈

- **框架**: FastAPI
- **ORM**: SQLAlchemy
- **数据库**: MySQL
- **数据源**: baostock / akshare

## 项目结构

```
seele-backend/
├── app/
│   ├── __init__.py
│   ├── config.py        # 配置文件（Pydantic Settings）
│   ├── database.py      # 数据库连接
│   ├── models.py        # 数据库模型
│   ├── schemas.py       # 请求响应模型
│   ├── crud.py          # 数据库 CRUD 操作
│   ├── indicators.py    # 股票指标计算
│   ├── main.py          # 主应用入口
│   └── routes/
│       ├── __init__.py
│       ├── stock_basic.py   # 股票基础数据接口
│       ├── stock_daily.py   # 股票日线数据接口
│       └── sync.py          # 数据同步接口
├── scripts/
│   ├── get_today_stock.py
│   └── sync_history_data.py
├── docs/
│   └── API.md           # 接口详细文档
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
├── .env                 # 环境变量（不提交）
└── start.py             # 启动脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=seele

APP_HOST=0.0.0.0
APP_PORT=9000
```

### 3. 创建数据库

```sql
CREATE DATABASE seele CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 启动服务

```bash
# 方式一：直接运行启动脚本（推荐，强制 9000 端口）
.venv/Scripts/python start.py

# 方式二：使用 uvicorn
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

启动后访问：

- API 文档: http://localhost:9000/docs
- 健康检查: http://localhost:9000/health

## 接口文档

详细接口说明见 [docs/API.md](docs/API.md)。

## 数据同步脚本

```bash
# 同步全部 A 股历史日线数据（2020-01-01 至今）
.venv/Scripts/python scripts/sync_history_data.py
```

## 文档同步规则

任何涉及接口参数、路由路径、响应结构的代码修改，**必须同步检查并更新 `docs/API.md`**。
