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
   * 录入做T交易记录
   * @param {Object} data
   * @param {string} data.symbol - 股票代码
   * @param {string} data.name - 股票名称
   * @param {string} data.trade_date - 交易日期 YYYY-MM-DD
   * @param {number} data.buy_price - 买入价格
   * @param {number} data.sell_price - 卖出价格
   * @param {number} data.quantity - 成交股数
   */
  createDayTrade (data) {
    return request({
      url: '/portfolio/day-trades',
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
        page_size: 10,
        ...params
      }
    })
  },

  /**
   * 更新交易记录
   * @param {number} id
   * @param {Object} data
   */
  updateTrade (id, data) {
    return request({
      url: `/portfolio/trades/${id}`,
      method: 'put',
      data
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
   * 同步持仓快照
   */
  syncPositions () {
    return request({
      url: '/portfolio/sync',
      method: 'post'
    })
  },

  /**
   * 重建每日资产数据（修复历史日线补齐后资产趋势断层）
   */
  rebuildDailyData () {
    return request({
      url: '/portfolio/rebuild-daily',
      method: 'post'
    })
  },

  /**
   * 获取当前持仓
   */
  getPositions (group) {
    return request({
      url: '/portfolio/positions',
      method: 'get',
      params: group ? { group } : {}
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
        page_size: 10,
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
   * 更新持仓（止损止盈、分组、备注）
   * @param {string} symbol - 股票代码
   * @param {Object} data
   */
  updatePosition (symbol, data) {
    return request({
      url: `/portfolio/positions/${symbol}`,
      method: 'put',
      data
    })
  },

  /**
   * 获取持仓预警
   */
  getAlerts () {
    return request({
      url: '/portfolio/alerts',
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
   * @param {number} [data.commission_rate] - 佣金费率
   * @param {number} [data.stamp_tax_rate] - 印花税税率
   * @param {number} [data.transfer_rate] - 过户费费率
   */
  updateConfig (data) {
    return request({
      url: '/portfolio/config',
      method: 'put',
      data
    })
  }
}
