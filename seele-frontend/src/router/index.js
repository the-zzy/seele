import { createRouter, createWebHistory } from 'vue-router'
import StockListView from '../views/StockListView.vue'
import StockIndicatorView from '../views/StockIndicatorView.vue'
import StockBasicView from '../views/StockBasicView.vue'
import StockKLineView from '../views/StockKLineView.vue'
import ChgDistributionView from '../views/ChgDistributionView.vue'
import PortfolioView from '../views/PortfolioView.vue'
import MainwaveView from '../views/MainwaveView.vue'
import MainwavePickerView from '../views/MainwavePickerView.vue'
import MainwaveScorerView from '../views/MainwaveScorerView.vue'
import StockFinancialView from '../views/StockFinancialView.vue'
import FinancialListView from '../views/FinancialListView.vue'
import SyncJobLogView from '../views/SyncJobLogView.vue'
import AgentView from '../views/AgentView.vue'
import BoardListView from '../views/BoardListView.vue'
import BoardDetailView from '../views/BoardDetailView.vue'
import SystemLogView from '../views/SystemLogView.vue'
import GalleryView from '../views/GalleryView.vue'

const routes = [
  {
    path: '/',
    name: 'gallery',
    component: GalleryView,
    meta: { title: '图库', nav: true, navOrder: 5, section: '主页' }
  },
  {
    path: '/stock-basic',
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
    path: '/portfolio',
    name: 'portfolio',
    component: PortfolioView,
    meta: { title: '持仓管理', nav: true, navOrder: 40, section: '资产' }
  },
  {
    path: '/mainwave/picker',
    name: 'mainwave-picker',
    component: MainwavePickerView,
    meta: { title: '选股', nav: true, navOrder: 50, group: '主升浪' }
  },
  {
    path: '/mainwave/scorer',
    name: 'mainwave-scorer',
    component: MainwaveScorerView,
    meta: { title: '评分', nav: true, navOrder: 51, group: '主升浪' }
  },
  {
    path: '/mainwave/group',
    name: 'mainwave-group',
    component: MainwaveView,
    meta: { title: '分组', nav: true, navOrder: 52, group: '主升浪' }
  },
  {
    path: '/mainwave',
    redirect: '/mainwave/picker'
  },
  {
    path: '/mainwave-picker',
    redirect: '/mainwave/picker'
  },
  {
    path: '/mainwave-scorer',
    redirect: '/mainwave/scorer'
  },
  {
    path: '/sync-jobs',
    name: 'sync-jobs',
    component: SyncJobLogView,
    meta: { title: '同步任务', nav: true, navOrder: 90, section: '系统' }
  },
  {
    path: '/system-logs',
    name: 'system-logs',
    component: SystemLogView,
    meta: { title: '系统日志', nav: true, navOrder: 91, section: '系统' }
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
  },
  {
    path: '/agent',
    name: 'agent',
    component: AgentView,
    meta: { title: 'AI Agent', nav: true, navOrder: 100, section: '智能助手' }
  },
  {
    path: '/boards',
    name: 'board-list',
    component: BoardListView,
    meta: { title: '板块 / ETF', nav: true, navOrder: 35, section: '市场数据' }
  },
  {
    path: '/boards/:code',
    name: 'board-detail',
    component: BoardDetailView,
    meta: { title: '板块详情' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const inWorkspace = localStorage.getItem('seele_workspace') === '1'
  if (!inWorkspace && to.path !== '/') {
    next('/')
    return
  }
  next()
})

router.afterEach((to) => {
  const title = to.meta?.title || 'Seele'
  document.title = `${title} · Seele`
})

export default router
