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

  // 缓存按日期查询的全量数据，避免翻页重复请求
  const cacheKey = ref(null)
  const cachedList = ref([])

  // 总页数
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

  function buildCacheKey (params) {
    return JSON.stringify({
      tradeDate: params.tradeDate,
      excludeSt: params.excludeSt,
      excludeCyb: params.excludeCyb,
      excludeKcb: params.excludeKcb,
      excludeBse: params.excludeBse,
      symbol: params.symbol
    })
  }

  function compareForSort (a, b) {
    if (a == null && b == null) return 0
    if (a == null) return 1
    if (b == null) return -1
    if (typeof a === 'number' && typeof b === 'number') {
      return a - b
    }
    return String(a).localeCompare(String(b), undefined, { numeric: true })
  }

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
      // 有交易日期时，使用 getAllByTradeDate 获取关联好的数据
      if (params.tradeDate) {
        const currentKey = buildCacheKey(params)
        let list = cachedList.value

        if (cacheKey.value !== currentKey) {
          const data = await stockDailyApi.getAllByTradeDate(params.tradeDate, {
            exclude_st: params.excludeSt || false,
            exclude_cyb: params.excludeCyb || false,
            exclude_kcb: params.excludeKcb || false,
            exclude_bse: params.excludeBse || false
          })
          list = (data?.list || []).map(item => ({
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

          // 排除ST、创业板、科创板、北交所筛选
          if (params.excludeSt) {
            list = list.filter(item => !item.name?.includes('ST'))
          }
          if (params.excludeCyb) {
            list = list.filter(item =>
              !item.symbol?.startsWith('300') &&
              !item.symbol?.startsWith('301')
            )
          }
          if (params.excludeKcb) {
            list = list.filter(item =>
              !item.symbol?.startsWith('688') &&
              !item.symbol?.startsWith('689')
            )
          }
          if (params.excludeBse) {
            list = list.filter(item =>
              !item.symbol?.startsWith('4') &&
              !item.symbol?.startsWith('8')
            )
          }

          // 代码筛选
          const symbolFilter = params.symbol?.trim()
          if (symbolFilter) {
            list = list.filter(item =>
              item.symbol?.includes(symbolFilter) ||
              item.name?.includes(symbolFilter)
            )
          }

          cachedList.value = list
          cacheKey.value = currentKey
        }

        // 排序（每次都要重新应用，支持切换排序不重复请求）
        const sortField = params.sortField || 'symbol'
        const sortOrder = params.sortOrder || 'asc'
        list.sort((a, b) => {
          const result = compareForSort(a[sortField], b[sortField])
          return sortOrder === 'asc' ? result : -result
        })

        // 手动分页
        total.value = list.length
        const start = (pageNum.value - 1) * pageSize.value
        const end = start + pageSize.value
        stockList.value = list.slice(start, end)
        return
      }

      // 无交易日期时清空日期缓存
      cacheKey.value = null
      cachedList.value = []

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
    cacheKey.value = null
    cachedList.value = []
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
