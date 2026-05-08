import { ref, computed } from 'vue'
import { stockDailyApi, stockBasicApi } from '@/api/stock'

/**
 * 股票数据管理的可复用逻辑
 */
export function useStockData () {
  // 加载状态
  const loading = ref(false)

  // 数据列表
  const stockList = ref([])
  const total = ref(0)
  const pageNum = ref(1)
  const pageSize = ref(100)

  // 总页数
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

  /**
   * 加载股票数据
   * @param {Object} params - 查询参数
   * @param {string} params.tradeDate - 交易日期（可选，有则查询该日期的日线数据）
   * @param {string} params.symbol - 股票代码筛选（可选）
   * @param {string} params.sortField - 排序字段
   * @param {string} params.sortOrder - 排序方向
   */
  async function loadStockData (params = {}) {
    loading.value = true
    try {
      // 有交易日期时，服务端分页获取
      if (params.tradeDate) {
        const data = await stockDailyApi.getAllByTradeDate(params.tradeDate, {
          exclude_st: params.excludeSt || false,
          exclude_cyb: params.excludeCyb || false,
          exclude_kcb: params.excludeKcb || false,
          exclude_bse: params.excludeBse || false,
          symbol: params.symbol || undefined,
          sort_field: params.sortField || 'symbol',
          sort_order: params.sortOrder || 'asc',
          page_num: pageNum.value,
          page_size: pageSize.value
        })
        stockList.value = (data?.list || []).map(item => ({
          id: item.id,
          symbol: item.symbol,
          name: item.stock_name || item.name || '-',
          area: item.area || '-',
          industry: item.industry || '-',
          market: item.market || '-',
          tradeDate: item.trade_date,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
          volume: item.volume,
          amount: item.amount,
          amplitude: item.amplitude,
          pctChg: item.pct_chg,
          priceChange: item.price_change,
          turnover: item.turnover,
          ma5: item.ma5,
          ma10: item.ma10,
          ma20: item.ma20,
          ma30: item.ma30,
          ma60: item.ma60,
          volMa5: item.vol_ma5,
          volMa10: item.vol_ma10,
          turnoverMa5: item.turnover_ma5,
          turnoverMa10: item.turnover_ma10
        }))
        total.value = data?.total || 0
        return
      }

      // 无交易日期时，只查询基础数据
      const basicData = await stockBasicApi.pageQuery({
        page_num: pageNum.value,
        page_size: pageSize.value,
        sort_field: params.sortField || 'symbol',
        sort_order: params.sortOrder || 'asc',
        symbol: params.symbol || undefined,
        exclude_st: params.excludeSt || false,
        exclude_cyb: params.excludeCyb || false,
        exclude_kcb: params.excludeKcb || false,
        exclude_bse: params.excludeBse || false
      })

      stockList.value = (basicData?.list || []).map(item => ({
        id: item.id,
        symbol: item.symbol,
        name: item.name,
        area: item.area || '-',
        industry: item.industry || '-',
        market: item.market || '-',
        tradeDate: null,
        open: null,
        high: null,
        low: null,
        close: null,
        volume: null,
        amount: null,
        amplitude: null,
        pctChg: null,
        priceChange: null,
        turnover: null
      }))
      total.value = basicData?.total || 0
    } catch (error) {
      console.error('加载股票数据失败:', error)
      stockList.value = []
      total.value = 0
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置页码并加载数据
   * @param {number} newPage - 新页码
   * @param {Object} params - 查询参数
   */
  async function setPage (newPage, params = {}) {
    pageNum.value = newPage
    await loadStockData(params)
  }

  /**
   * 设置每页条数并加载数据
   * @param {number} newSize - 新页大小
   * @param {Object} params - 查询参数
   */
  async function setPageSize (newSize, params = {}) {
    pageSize.value = newSize
    pageNum.value = 1
    await loadStockData(params)
  }

  function clearCache () {
    pageNum.value = 1
  }

  return {
    loading,
    stockList,
    total,
    pageNum,
    pageSize,
    totalPages,
    loadStockData,
    setPage,
    setPageSize,
    clearCache
  }
}
