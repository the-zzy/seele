import request from '@/utils/request'

/**
 * 股票日线数据 API
 */
export const stockDailyApi = {
  /**
   * 分页查询股票日线数据
   * @param {Object} params - 查询参数
   * @param {string} params.symbol - 股票代码（可选）
   * @param {string} params.startDate - 开始日期（可选）
   * @param {string} params.endDate - 结束日期（可选）
   * @param {number} params.pageNum - 页码，默认 1
   * @param {number} params.pageSize - 每页条数，默认 10
   * @returns {Promise<PageResult>}
   */
  pageQuery (params) {
    return request({
      url: '/stock/daily/page',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 10,
        ...params
      }
    })
  },

  /**
   * 根据交易日期查询股票日线数据
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {Promise<Array>}
   */
  getByTradeDate (tradeDate) {
    return request({
      url: `/stock/daily/date/${tradeDate}`,
      method: 'get'
    })
  },

  /**
   * 根据股票代码查询日线数据
   * @param {string} symbol - 股票代码
   * @returns {Promise<Array>}
   */
  getBySymbol (symbol) {
    return request({
      url: `/stock/daily/symbol/${symbol}`,
      method: 'get'
    })
  },

  /**
   * 批量查询股票日线数据
   * @param {Array<string>} symbols - 股票代码数组
   * @returns {Promise<Array>}
   */
  getBySymbols (symbols) {
    return request({
      url: '/stock/daily/symbols',
      method: 'post',
      data: symbols
    })
  },

  /**
   * 获取交易日列表
   * @returns {Promise<Array<string>>} - 交易日列表（按升序排列，格式：YYYY-MM-DD）
   */
  getTradeDates () {
    return request({
      url: '/stock/daily/trade-dates',
      method: 'get'
    })
  },

  /**
   * 根据交易日期分页获取A股数据（关联basic表）
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @param {Object} query - 查询参数
   * @returns {Promise<Object>} - {trade_date, total, page_num, page_size, list}
   */
  getAllByTradeDate (tradeDate, query = {}) {
    return request({
      url: `/stock/daily/date/${tradeDate}/all`,
      method: 'get',
      params: query
    })
  },

  /**
   * 统计日期范围内每天涨幅超过阈值的股票占比（柱状图）
   * @param {string} startDate - 开始日期 (YYYY-MM-DD)
   * @param {string} endDate - 结束日期 (YYYY-MM-DD)
   * @param {number} threshold - 涨幅阈值百分比，默认 2.0
   * @returns {Promise<Object>} - {start_date, end_date, threshold, list}
   */
  getPctChgDistribution (startDate, endDate, threshold = 2.0) {
    return request({
      url: '/market/sentiment/daily',
      method: 'get',
      params: {
        start_date: startDate,
        end_date: endDate,
        threshold
      }
    })
  },

  /**
   * 主升浪选股（关联日线及指标表，支持市值/股价/换手率/成交额筛选）
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期(YYYY-MM-DD)
   * @param {number} params.float_market_cap_min - 流通市值最小值(亿元)
   * @param {number} params.close_max - 收盘价最大值
   * @param {number} params.avg_turnover_min - 10日平均换手率最小值(%)
   * @param {number} params.avg_amount_min - 10日平均成交额最小值(元)
   * @returns {Promise<Object>}
   */
  getMainwavePicker (params = {}) {
    return request({
      url: '/stock/daily/mainwave-picker',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 10,
        sort_field: 'symbol',
        sort_order: 'asc',
        ...params
      }
    })
  }
}

/**
 * 市场情绪 API
 */
export const marketSentimentApi = {
  /**
   * 查询日期范围内的每日市场情绪统计
   * @param {string} startDate - 开始日期 (YYYY-MM-DD)
   * @param {string} endDate - 结束日期 (YYYY-MM-DD)
   * @returns {Promise<Object>}
   */
  getDailySentiment (startDate, endDate) {
    return request({
      url: '/market/sentiment/daily',
      method: 'get',
      params: { start_date: startDate, end_date: endDate }
    })
  },

  /**
   * 查询某日的板块情绪统计
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {Promise<Object>}
   */
  getIndustrySentiment (tradeDate) {
    return request({
      url: '/market/sentiment/industry',
      method: 'get',
      params: { trade_date: tradeDate }
    })
  }
}

/**
 * 股票日线指标 API
 */
export const stockIndicatorApi = {
  /**
   * 计算指定日期的日线指标
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {Promise<Object>}
   */
  compute (tradeDate) {
    return request({
      url: '/stock/indicator/compute',
      method: 'post',
      params: { trade_date: tradeDate }
    })
  },

  /**
   * 根据股票代码查询指标
   * @param {string} symbol - 股票代码
   * @returns {Promise<Array>}
   */
  getBySymbol (symbol) {
    return request({
      url: `/stock/indicator/symbol/${symbol}`,
      method: 'get'
    })
  },

  /**
   * 根据交易日期查询指标
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {Promise<Array>}
   */
  getByDate (tradeDate) {
    return request({
      url: `/stock/indicator/date/${tradeDate}`,
      method: 'get'
    })
  }
}

/**
 * 数据同步 API
 */
export const syncApi = {
  syncByDate (tradeDate) {
    return request({
      url: `/sync/daily/date/${tradeDate}`,
      method: 'post',
      timeout: 600000
    })
  },

  syncAll () {
    return request({
      url: '/sync/daily',
      method: 'post'
    })
  },

  syncStockBasic () {
    return request({
      url: '/sync/stock-basic',
      method: 'post',
      timeout: 120000
    })
  },

  syncFinancial () {
    return request({
      url: '/sync/financial',
      method: 'post',
      timeout: 600000
    })
  },

  syncIndicator (tradeDate) {
    return request({
      url: '/sync/indicator',
      method: 'post',
      params: { trade_date: tradeDate },
      timeout: 600000
    })
  },

  createSyncStream (tradeDate) {
    const base = process.env.NODE_ENV === 'production'
      ? (process.env.VUE_APP_BASE_API || '/api')
      : 'http://localhost:9000/api'
    return new EventSource(`${base}/sync/daily/date/${tradeDate}/stream`)
  },

  getJobLogs (days = 5, jobType = null) {
    return request({
      url: '/sync/job-logs',
      method: 'get',
      params: {
        days,
        job_type: jobType
      }
    })
  },

  getDbStatus () {
    return request({
      url: '/sync/db-status',
      method: 'get'
    })
  },

  getTaskStatus (taskId) {
    return request({
      url: `/sync/task/${taskId}`,
      method: 'get'
    })
  },

  getLatestTradeDate () {
    return request({
      url: '/sync/latest-trade-date',
      method: 'get'
    })
  },

  getDetailedStatus () {
    return request({
      url: '/sync/detailed-status',
      method: 'get'
    })
  }
}

/**
 * 股票基础信息 API
 */
export const stockBasicApi = {
  pageQuery (params = {}) {
    return request({
      url: '/stock/basic/page',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 10,
        sort_field: 'symbol',
        sort_order: 'asc',
        ...params
      }
    })
  },

  listAll (pageNum = 1, pageSize = 10) {
    return request({
      url: '/stock/basic/list',
      method: 'get',
      params: {
        page_num: pageNum,
        page_size: pageSize
      }
    })
  },

  getBySymbol (symbol) {
    return request({
      url: `/stock/basic/symbol/${symbol}`,
      method: 'get'
    })
  }
}
