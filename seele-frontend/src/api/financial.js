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
        page_size: 10,
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

}
