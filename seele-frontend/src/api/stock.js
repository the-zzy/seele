import request from '@/utils/request'

/**
 * 股票日线数据 API
 */
export const stockDailyApi = {
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
   * 批量获取指定日期收盘价
   * @param {string} symbols - 股票代码，逗号分隔
   * @param {string} tradeDate - 交易日期 YYYY-MM-DD
   * @returns {Promise<Object>} - {symbol: {close, trade_date}}
   */
  getCloseByDate (symbols, tradeDate) {
    return request({
      url: '/stock/daily/close',
      method: 'get',
      params: { symbols, trade_date: tradeDate }
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
 * 指数数据 API
 */
export const indexApi = {
  getIndexList () {
    return request({
      url: '/index/list',
      method: 'get'
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
  }
}

/**
 * 数据同步 API
 */
export const syncApi = {
  syncByDate (tradeDate, onlyMissing = false) {
    return request({
      url: `/sync/daily/date/${tradeDate}`,
      method: 'post',
      params: { only_missing: onlyMissing },
      timeout: 600000
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

  syncIndicator (tradeDate, onlyMissing = false) {
    return request({
      url: '/sync/indicator',
      method: 'post',
      params: { trade_date: tradeDate, only_missing: onlyMissing },
      timeout: 600000
    })
  },

  syncSingleStock (symbol, tradeDate) {
    return request({
      url: `/sync/daily/stock/${symbol}/date/${tradeDate}`,
      method: 'post',
      timeout: 600000
    })
  },

  getJobLogs (days = 5, jobType = null, pageNum = 1, pageSize = 10) {
    return request({
      url: '/sync/job-logs',
      method: 'get',
      params: {
        days,
        job_type: jobType,
        page_num: pageNum,
        page_size: pageSize
      }
    })
  },

  getTaskStatus (taskId) {
    return request({
      url: `/sync/task/${taskId}`,
      method: 'get'
    })
  },

  getActiveTasks () {
    return request({
      url: '/sync/active-tasks',
      method: 'get'
    })
  },

  cancelTask (taskId) {
    return request({
      url: `/sync/task/${taskId}/cancel`,
      method: 'post'
    })
  },

  getDetailedStatus (dailyPageNum = 1, dailyPageSize = 5) {
    return request({
      url: '/sync/detailed-status',
      method: 'get',
      params: {
        daily_page_num: dailyPageNum,
        daily_page_size: dailyPageSize
      }
    })
  },

  cancelJobLog (logId) {
    return request({
      url: `/sync/job-log/${logId}/cancel`,
      method: 'post'
    })
  },

  startPipeline (chainType, tradeDate = null) {
    return request({
      url: '/sync/pipeline',
      method: 'post',
      data: {
        chain_type: chainType,
        trade_date: tradeDate
      },
      timeout: 30000
    })
  },

  getPipeline (pipelineId) {
    return request({
      url: `/sync/pipeline/${pipelineId}`,
      method: 'get'
    })
  },

  getPipelines () {
    return request({
      url: '/sync/pipelines',
      method: 'get'
    })
  },

  cancelPipeline (pipelineId) {
    return request({
      url: `/sync/pipeline/${pipelineId}/cancel`,
      method: 'post'
    })
  }
}

/**
 * 交易日历 API
 */
export const tradeCalendarApi = {
  getLatest () {
    return request({
      url: '/trade-calendar/latest',
      method: 'get'
    })
  }
}

/**
 * 板块/ETF API
 */
export const boardApi = {
  getList (params = {}) {
    return request({
      url: '/board/list',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 50,
        ...params
      }
    })
  },

  getDaily (params = {}) {
    return request({
      url: '/board/daily',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 50,
        ...params
      }
    })
  },

  getConstituents (code) {
    return request({
      url: `/board/constituents/${code}`,
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
  }
}
