import request from '@/utils/request'

/**
 * 财务指标 API
 */
export const financialApi = {
  /**
   * 查询财务指标列表
   * @param {Object} params
   */
  getList (params = {}) {
    return request({
      url: '/financial',
      method: 'get',
      params: {
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 获取单只股票财务指标
   * @param {string} symbol
   */
  getBySymbol (symbol) {
    return request({
      url: `/financial/${symbol}`,
      method: 'get'
    })
  },

  /**
   * 财务选股
   * @param {Object} data
   */
  picker (data = {}) {
    return request({
      url: '/financial/picker',
      method: 'post',
      data
    })
  },

  /**
   * 同步全部股票财务指标
   */
  syncAll () {
    return request({
      url: '/sync/financial',
      method: 'post'
    })
  },

  /**
   * 创建财务指标同步 SSE 实时进度流
   * @returns {EventSource}
   */
  createFinancialSyncStream () {
    const base = process.env.NODE_ENV === 'production'
      ? (process.env.VUE_APP_BASE_API || '/api')
      : 'http://localhost:9000/api'
    return new EventSource(`${base}/sync/financial/stream`)
  },

  /**
   * 同步单只股票财务指标
   * @param {string} symbol
   */
  syncBySymbol (symbol) {
    return request({
      url: `/sync/financial/${symbol}`,
      method: 'post'
    })
  }
}
