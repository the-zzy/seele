import request from '@/utils/request'

/**
 * 持仓管理 API
 */
export const portfolioApi = {
  /**
   * 录入交易记录
   * @param {Object} data
   * @param {string} data.symbol - 股票代码
   * @param {string} data.name - 股票名称
   * @param {string} data.trade_type - BUY / SELL
   * @param {string} data.trade_date - 交易日期 YYYY-MM-DD
   * @param {number} data.price - 成交价格
   * @param {number} data.quantity - 成交股数
   * @param {number} [data.amount] - 成交金额（可选，不传自动计算）
   */
  createTrade (data) {
    return request({
      url: '/portfolio/trades',
      method: 'post',
      data
    })
  },

  /**
   * 查询交易记录列表
   * @param {Object} params
   */
  getTrades (params = {}) {
    return request({
      url: '/portfolio/trades',
      method: 'get',
      params: {
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 删除交易记录
   * @param {number} id
   */
  deleteTrade (id) {
    return request({
      url: `/portfolio/trades/${id}`,
      method: 'delete'
    })
  },

  /**
   * 获取当前持仓
   */
  getPositions () {
    return request({
      url: '/portfolio/positions',
      method: 'get'
    })
  },

  /**
   * 获取已清仓记录
   * @param {Object} params
   */
  getClosed (params = {}) {
    return request({
      url: '/portfolio/closed',
      method: 'get',
      params: {
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 获取资产总览
   */
  getSummary () {
    return request({
      url: '/portfolio/summary',
      method: 'get'
    })
  },

  /**
   * 获取每日盈亏时间序列
   */
  getDailyPnl () {
    return request({
      url: '/portfolio/daily-pnl',
      method: 'get'
    })
  },

  /**
   * 获取持仓市值分布
   */
  getDistribution () {
    return request({
      url: '/portfolio/distribution',
      method: 'get'
    })
  },

  /**
   * 获取持仓配置
   */
  getConfig () {
    return request({
      url: '/portfolio/config',
      method: 'get'
    })
  },

  /**
   * 更新持仓配置
   * @param {Object} data
   * @param {number} data.initial_capital - 初始资金
   */
  updateConfig (data) {
    return request({
      url: '/portfolio/config',
      method: 'put',
      data
    })
  }
}
