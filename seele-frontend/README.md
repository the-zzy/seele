# Seele 前端

基于 Vue 3 的股票数据管理前端应用。

## 技术栈

- **框架**: Vue 3.2.13
- **构建工具**: Vue CLI 5.x
- **路由**: Vue Router 4
- **状态管理**: Vuex 4
- **HTTP 客户端**: Axios
- **图表**: ECharts 6.0.0
- **样式**: SCSS/Sass

## 项目结构

```
src/
├── main.js              # 应用入口
├── App.vue              # 根组件
├── api/
│   ├── financial.js     # 财务指标 API
│   ├── portfolio.js     # 持仓管理 API
│   └── stock.js         # 股票数据 API
├── components/
│   ├── common/          # 通用组件
│   │   ├── BasePagination.vue
│   │   ├── PageHero.vue
│   │   └── SyncProgress.vue
│   ├── portfolio/       # 持仓相关组件
│   │   ├── PortfolioPositionTable.vue
│   │   ├── PortfolioStatsCards.vue
│   │   ├── PortfolioTradeModal.vue
│   │   └── PortfolioTradeTable.vue
│   └── stock/           # 股票相关组件
│       ├── FinancialListTable.vue
│       ├── StockBasicFilter.vue
│       ├── StockBasicTable.vue
│       ├── StockDataTable.vue
│       ├── StockFilterPanel.vue
│       └── StockIndicatorTable.vue
├── composables/         # 组合式函数
│   ├── useEChart.js
│   ├── useStockData.js
│   └── useTheme.js
├── router/
│   └── index.js         # 路由配置
├── styles/
│   ├── global.scss
│   └── variables.scss
├── utils/
│   ├── date.js
│   ├── formatters.js
│   └── request.js
└── views/               # 页面视图
    ├── ChgDistributionView.vue
    ├── FinancialListView.vue
    ├── IndustrySentimentView.vue
    ├── MainwavePickerView.vue
    ├── PortfolioView.vue
    ├── StockBasicView.vue
    ├── StockFinancialView.vue
    ├── StockIndicatorView.vue
    ├── StockKLineView.vue
    └── StockListView.vue
```

## 页面路由

| 路径 | 页面 |
|------|------|
| `/` | 股票基本信息 |
| `/financial` | 财务指标 |
| `/daily/basic` | 基本数据 |
| `/daily/indicator` | 指标数据 |
| `/chg-distribution` | 涨幅分布统计 |
| `/industry-sentiment` | 板块情绪分布 |
| `/portfolio` | 持仓管理 |
| `/mainwave-picker` | 主升浪选股 |
| `/kline/:symbol` | K 线图 |
| `/financial/:symbol` | 财务分析 |

## 开发规范

- 使用 Composition API + `<script setup>` 语法
- 组件名 PascalCase，Props camelCase（模板中使用 kebab-case）
- 逻辑抽入 composables，保持 View 组件薄
- Props down, Events up 为主模型

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（端口 8000）
npm run serve

# 构建生产环境
npm run build

# 代码检查
npm run lint
```

## 代理配置

`vue.config.js` 已配置开发服务器代理：

```javascript
devServer: {
  port: 8000,
  proxy: {
    '/api': {
      target: 'http://localhost:9000',
      changeOrigin: true
    }
  }
}
```

前端请求 `/api/xxx` 会自动转发到后端 `http://localhost:9000/api/xxx`。
