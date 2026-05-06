import { createRouter, createWebHistory } from 'vue-router'
import StockListView from '../views/StockListView.vue'
import StockIndicatorView from '../views/StockIndicatorView.vue'
import StockBasicView from '../views/StockBasicView.vue'
import StockKLineView from '../views/StockKLineView.vue'
import ChgDistributionView from '../views/ChgDistributionView.vue'
import ChgDistributionDetailView from '../views/ChgDistributionDetailView.vue'
import RangeStockPickerView from '../views/RangeStockPickerView.vue'
import TrendStockPickerView from '../views/TrendStockPickerView.vue'
import ShrinkingVolumePickerView from '../views/ShrinkingVolumePickerView.vue'
import BreakoutVolumePickerView from '../views/BreakoutVolumePickerView.vue'
import PortfolioView from '../views/PortfolioView.vue'

// nav 顺序：股票基本信息 → 股票日线数据(基本数据/指标数据) → 选股策略
const routes = [
  {
    path: '/',
    name: 'stock-basic',
    component: StockBasicView,
    meta: { title: '股票基本信息', nav: true, navOrder: 10, section: '基本面' }
  },
  {
    path: '/daily/basic',
    name: 'stock-list',
    component: StockListView,
    meta: { title: '基本数据', nav: true, navOrder: 20, group: '股票日线数据' }
  },
  {
    path: '/daily/indicator',
    name: 'stock-indicator',
    component: StockIndicatorView,
    meta: { title: '指标数据', nav: true, navOrder: 21, group: '股票日线数据' }
  },
  {
    path: '/chg-distribution',
    name: 'chg-distribution',
    component: ChgDistributionView,
    meta: { title: '涨幅分布统计', nav: true, navOrder: 30, group: '选股策略' }
  },
  {
    path: '/range-picker',
    name: 'range-picker',
    component: RangeStockPickerView,
    meta: { title: '震荡选股策略', nav: true, navOrder: 31, group: '选股策略' }
  },
  {
    path: '/trend-picker',
    name: 'trend-picker',
    component: TrendStockPickerView,
    meta: { title: '趋势选股策略', nav: true, navOrder: 32, group: '选股策略' }
  },
  {
    path: '/shrinking-volume',
    name: 'shrinking-volume',
    component: ShrinkingVolumePickerView,
    meta: { title: '缩量选股', nav: true, navOrder: 33, group: '选股策略' }
  },
  {
    path: '/breakout-volume',
    name: 'breakout-volume',
    component: BreakoutVolumePickerView,
    meta: { title: '倍量突破选股', nav: true, navOrder: 34, group: '选股策略' }
  },
  {
    path: '/chg-distribution/detail',
    name: 'chg-distribution-detail',
    component: ChgDistributionDetailView,
    meta: { title: '涨幅分布详情' }
  },
  {
    path: '/portfolio',
    name: 'portfolio',
    component: PortfolioView,
    meta: { title: '持仓管理', nav: true, navOrder: 40, section: '资产' }
  },
  {
    path: '/kline/:symbol',
    name: 'stock-kline',
    component: StockKLineView,
    meta: { title: 'K线图' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
