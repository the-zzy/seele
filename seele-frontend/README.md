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
│   └── stock.js         # 股票 API 请求封装
├── components/
│   ├── common/          # 通用组件
│   │   ├── BasePagination.vue
│   │   └── SyncProgress.vue
│   └── stock/           # 股票相关组件
│       ├── StockDataTable.vue
│       ├── StockFilterPanel.vue
│       ├── BreakoutPickerFilter.vue
│       ├── BreakoutPickerTable.vue
│       ├── RangePickerFilter.vue
│       ├── RangePickerTable.vue
│       ├── ShrinkingPickerFilter.vue
│       ├── ShrinkingPickerTable.vue
│       ├── TrendPickerFilter.vue
│       └── TrendPickerTable.vue
├── composables/         # 组合式函数
│   ├── useEChart.js
│   ├── useStockData.js
│   ├── useStockPicker.js
│   └── useTheme.js
├── router/
│   └── index.js         # 路由配置（8 个页面）
├── styles/
│   ├── global.scss
│   ├── variables.scss
│   └── _picker.scss
├── utils/
│   ├── date.js
│   ├── formatters.js
│   └── request.js
└── views/               # 页面视图
    ├── StockListView.vue
    ├── StockKLineView.vue
    ├── ClosingStockPickerView.vue
    ├── ClosingStockPickerDetailView.vue
    ├── RangeStockPickerView.vue
    ├── TrendStockPickerView.vue
    ├── ShrinkingVolumePickerView.vue
    └── BreakoutVolumePickerView.vue
```

## 页面路由

| 路径 | 页面 |
|------|------|
| `/` | 股票数据列表 |
| `/closing-picker` | 尾盘选股法 |
| `/closing-picker/detail` | 尾盘选股详情 |
| `/range-picker` | 震荡选股策略 |
| `/trend-picker` | 趋势选股策略 |
| `/kline/:symbol` | K 线图 |
| `/shrinking-volume` | 缩量选股 |
| `/breakout-volume` | 倍量突破选股 |

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
