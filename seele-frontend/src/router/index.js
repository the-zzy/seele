import { createRouter, createWebHistory } from 'vue-router'
import StockListView from '../views/StockListView.vue'
import StockIndicatorView from '../views/StockIndicatorView.vue'
import StockBasicView from '../views/StockBasicView.vue'
import StockKLineView from '../views/StockKLineView.vue'
import ChgDistributionView from '../views/ChgDistributionView.vue'
import PortfolioView from '../views/PortfolioView.vue'
import MainwavePickerView from '../views/MainwavePickerView.vue'
import IndustrySentimentView from '../views/IndustrySentimentView.vue'
import StockFinancialView from '../views/StockFinancialView.vue'
import FinancialListView from '../views/FinancialListView.vue'
import SyncJobLogView from '../views/SyncJobLogView.vue'

const routes = [
  {
    path: '/',
    name: 'stock-basic',
    component: StockBasicView,
    meta: { title: '股票基本信息', nav: true, navOrder: 10, section: '基本面' }
  },
  {
    path: '/financial',
    name: 'financial-list',
    component: FinancialListView,
    meta: { title: '财务指标', nav: true, navOrder: 11, section: '基本面' }
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
    meta: { title: '涨幅分布统计', nav: true, navOrder: 30, group: '市场情绪' }
  },
  {
    path: '/industry-sentiment',
    name: 'industry-sentiment',
    component: IndustrySentimentView,
    meta: { title: '板块情绪分布', nav: true, navOrder: 31, group: '市场情绪' }
  },
  {
    path: '/portfolio',
    name: 'portfolio',
    component: PortfolioView,
    meta: { title: '持仓管理', nav: true, navOrder: 40, section: '资产' }
  },
  {
    path: '/mainwave-picker',
    name: 'mainwave-picker',
    component: MainwavePickerView,
    meta: { title: '主升浪选股', nav: true, navOrder: 50, section: '选股策略' }
  },
  {
    path: '/sync-jobs',
    name: 'sync-jobs',
    component: SyncJobLogView,
    meta: { title: '同步任务', nav: true, navOrder: 90, section: '系统' }
  },
  {
    path: '/kline/:symbol',
    name: 'stock-kline',
    component: StockKLineView,
    meta: { title: 'K线图' }
  },
  {
    path: '/financial/:symbol',
    name: 'stock-financial',
    component: StockFinancialView,
    meta: { title: '财务分析' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
