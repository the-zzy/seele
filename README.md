# Seele 股票数据管理系统

Seele 是一个基于 Vue 3 + FastAPI 的全栈股票数据管理系统，提供股票列表展示、K 线图、多种选股策略（尾盘选股、震荡选股、趋势选股、缩量选股、倍量突破选股）等功能。

## 目录结构

```
d:\code
├── seele-backend/          # FastAPI 后端
│   ├── app/                # 主应用包
│   │   ├── routes/         # API 路由层
│   │   ├── models.py       # 数据模型层
│   │   ├── schemas.py      # 数据校验层
│   │   ├── crud.py         # 数据访问层
│   │   ├── indicators.py   # 股票指标计算
│   │   ├── main.py         # 应用入口
│   │   └── ...
│   ├── scripts/            # 独立工具脚本
│   │   ├── get_today_stock.py
│   │   └── sync_history_data.py
│   ├── docs/               # 接口文档
│   ├── requirements.txt    # Python 依赖
│   ├── .env                # 环境变量（不提交）
│   └── start.py            # 启动脚本
│
├── seele-frontend/         # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面层
│   │   ├── components/     # 组件层
│   │   ├── composables/    # 逻辑复用层
│   │   ├── api/            # 接口请求层
│   │   ├── router/         # 路由配置
│   │   ├── styles/         # 样式层
│   │   └── utils/          # 工具函数层
│   ├── package.json        # 项目依赖
│   └── vue.config.js       # Vue CLI 配置
│
├── package.json            # 根级脚本（一键启动）
├── .vscode/                # VS Code 工作区配置
└── README.md               # 本文件
```

## 快速开始

### 一键启动（推荐）

根目录已配置 `concurrently`，可同时启动前后端：

```bash
# 首次使用先安装根级依赖
npm install

# 同时启动前后端
npm run dev
```

### 单独启动

```bash
# 仅前端（端口 8000）
npm run dev:front

# 仅后端（端口 9000）
npm run dev:back
```

### 手动启动（传统方式）

```bash
# 后端
cd seele-backend
.venv/Scripts/python start.py

# 前端
cd seele-frontend
npm run serve
```

## 前后端分工

| 层级 | 技术栈 | 职责 |
|------|--------|------|
| **前端** | Vue 3 + Vue Router + Vuex + ECharts | UI 展示、选股策略交互、K 线图、数据可视化、用户操作响应 |
| **后端** | FastAPI + SQLAlchemy + MySQL | 数据爬取（akshare / baostock）、数据存储、指标计算、REST API 提供 |

### 接口约定

- 前后端通信统一走 `/api/*` 前缀。
- 前端 `vue.config.js` 已配置开发服务器代理，将 `/api` 请求转发到后端的 `http://localhost:9000`，开发环境无需处理跨域。
- 后端返回统一响应格式：`{ code: number, message: string, data: any }`。

## 端口规范

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端（Vue CLI） | **8000** | `vue.config.js` 已配置 `strictPort: true`，被占用会直接报错 |
| 后端（FastAPI） | **9000** | `start.py` 强制使用 9000 端口 |

> 启动前请检查端口是否被占用：`netstat -ano | grep -E ':(8000|9000)' | grep LISTENING`

## 开发规范

- **缩进**：2 空格
- **字符串**：单引号
- **分号**：末尾不加分号
- **换行符**：LF
- **Git 提交**：使用英文，遵循 conventional commits 格式
- **敏感信息**：绝不提交 API 密钥、密码等，不修改 `.env` 文件

### Vue.js 规范

- 使用 Composition API + `<script setup>` 语法
- 组件名 PascalCase，Props camelCase（模板中使用 kebab-case）

## 技术栈详情

### 前端

| 依赖 | 版本 | 说明 |
|------|------|------|
| vue | ^3.2.13 | 框架 |
| vue-router | ^4.0.3 | 路由 |
| vuex | ^4.0.0 | 状态管理 |
| axios | ^1.15.0 | HTTP 客户端 |
| echarts | ^6.0.0 | 图表库 |
| sass | ^1.32.7 | CSS 预处理器 |

### 后端

| 依赖 | 版本 | 说明 |
|------|------|------|
| fastapi | >=0.109.0 | Web 框架 |
| uvicorn | >=0.27.0 | ASGI 服务器 |
| sqlalchemy | >=2.0.25 | ORM |
| pydantic | >=2.5.3 | 数据校验 |
| akshare | >=1.12.0 | A 股数据源 |
| baostock | - | 备用数据源 |
| pandas | >=2.0.0 | 数据处理 |

## 子项目说明

- 后端详细说明 → [seele-backend/README.md](seele-backend/README.md)
- 前端详细说明 → [seele-frontend/README.md](seele-frontend/README.md)
- 后端接口文档 → [seele-backend/docs/API.md](seele-backend/docs/API.md)
