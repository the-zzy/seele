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
   * @param {number} params.pageSize - 每页条数，默认 20
   * @returns {Promise<PageResult>}
   */
  pageQuery (params) {
    return request({
      url: '/stock/daily/page',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 20,
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
   * @param {boolean} query.exclude_st - 是否过滤ST股票
   * @param {boolean} query.exclude_cyb - 是否过滤创业板
   * @param {boolean} query.exclude_kcb - 是否过滤科创板
   * @param {boolean} query.exclude_bse - 是否过滤北交所
   * @param {string} query.symbol - 代码或名称模糊搜索
   * @param {string} query.sort_field - 排序字段
   * @param {string} query.sort_order - 排序方向 asc/desc
   * @param {number} query.page_num - 页码
   * @param {number} query.page_size - 每页条数
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
   * @param {number} amountMa5Min - 5日平均成交额最小值，默认2亿
   * @param {number} amountMa10Min - 10日平均成交额最小值，默认2亿
   * @param {number} turnoverMa5Min - 5日平均换手率最小值，默认2%
   * @param {number} turnoverMa10Min - 10日平均换手率最小值，默认2%
   * @returns {Promise<Object>} - {start_date, end_date, threshold, list}
   */
  getPctChgDistribution (startDate, endDate, threshold = 2.0, amountMa5Min = 200000000, amountMa10Min = 200000000, turnoverMa5Min = 2, turnoverMa10Min = 2) {
    return request({
      url: '/stock/daily/pct-chg-distribution',
      method: 'get',
      params: {
        start_date: startDate,
        end_date: endDate,
        threshold,
        amount_ma5_min: amountMa5Min,
        amount_ma10_min: amountMa10Min,
        turnover_ma5_min: turnoverMa5Min,
        turnover_ma10_min: turnoverMa10Min
      }
    })
  },

  /**
   * 获取连续缩量的股票列表
   * @param {Object} params - 查询参数
   * @param {number} params.min_days - 最小连续缩量天数，默认 1
   * @param {number} params.max_days - 最大连续缩量天数，默认不限制
   * @param {number} params.lookback - 用于计算的历史交易日数量，默认 30，范围 10~120
   * @returns {Promise<Object>} - {min_days, max_days, total, list}
   */
  getShrinkingVolume (params = {}) {
    return request({
      url: '/stock/daily/shrinking-volume',
      method: 'get',
      params: {
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 倍量突破平台选股（数据库层计算）
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期 (YYYY-MM-DD)
   * @param {number} params.min_pct_chg - 最小涨幅，默认 3.0
   * @param {number} params.max_pct_chg - 最大涨幅，默认 7.0
   * @param {number} params.min_turnover - 最低换手率，默认 2.0
   * @param {number} params.min_amount - 最低成交额，默认 50000000
   * @param {boolean} params.exclude_st - 排除 ST，默认 true
   * @param {boolean} params.exclude_cyb - 排除创业板，默认 true
   * @param {boolean} params.exclude_kcb - 排除科创板，默认 true
   * @param {boolean} params.exclude_bse - 排除北交所，默认 true
   * @param {number} params.page_num - 页码，默认 1
   * @param {number} params.page_size - 每页条数，默认 20
   * @returns {Promise<Object>} - {trade_date, total, page_num, page_size, list}
   */
  getBreakoutPicker (params = {}) {
    return request({
      url: '/stock/daily/breakout-picker',
      method: 'post',
      data: {
        min_pct_chg: 3.0,
        max_pct_chg: 7.0,
        min_turnover: 2.0,
        min_amount: 50000000,
        exclude_st: true,
        exclude_cyb: true,
        exclude_kcb: true,
        exclude_bse: true,
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 趋势选股
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期 (YYYY-MM-DD)
   * @param {number} params.min_pct_chg - 最小涨幅，默认 2.0
   * @param {number} params.max_pct_chg - 最大涨幅，默认 8.0
   * @param {number} params.min_turnover - 最低换手率，默认 2.0
   * @param {number} params.min_amount - 最低成交额均值(10日)，默认 200000000
   * @param {boolean} params.ma_alignment - 均线多头排列，默认 true
   * @param {boolean} params.macd_golden_cross - MACD金叉，默认 false
   * @param {number} params.rsi_min - RSI最小值，默认 40
   * @param {number} params.rsi_max - RSI最大值，默认 80
   * @param {number} params.volume_ratio - 成交量/20日均量，默认 1.5
   * @param {boolean} params.exclude_st - 排除 ST，默认 true
   * @param {boolean} params.exclude_cyb - 排除创业板，默认 true
   * @param {boolean} params.exclude_kcb - 排除科创板，默认 true
   * @param {boolean} params.exclude_bse - 排除北交所，默认 true
   * @param {string} params.sort_field - 排序字段，默认 pct_chg
   * @param {string} params.sort_order - 排序方向，默认 desc
   * @param {number} params.page_num - 页码，默认 1
   * @param {number} params.page_size - 每页条数，默认 20
   * @returns {Promise<Object>} - {trade_date, total, page_num, page_size, list}
   */
  getTrendPicker (params = {}) {
    return request({
      url: '/stock/daily/trend-picker',
      method: 'post',
      data: {
        min_pct_chg: 2.0,
        max_pct_chg: 8.0,
        min_turnover: 2.0,
        min_amount: 200000000,
        ma_alignment: true,
        macd_golden_cross: false,
        rsi_min: 40,
        rsi_max: 80,
        volume_ratio: 1.5,
        exclude_st: true,
        exclude_cyb: true,
        exclude_kcb: true,
        exclude_bse: true,
        sort_field: 'pct_chg',
        sort_order: 'desc',
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 震荡选股
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期 (YYYY-MM-DD)
   * @param {number} params.max_pct_chg_20d - 近20日涨幅绝对值均值上限，默认 10.0
   * @param {number} params.min_amplitude_20d - 近20日平均振幅最小值，默认 3.0
   * @param {number} params.bb_width_max - 布林带宽度最大值，默认 0.08
   * @param {number} params.rsi_min - RSI最小值，默认 35
   * @param {number} params.rsi_max - RSI最大值，默认 65
   * @param {boolean} params.volume_shrink - 近期缩量，默认 true
   * @param {boolean} params.near_ma20 - 收盘价在MA20附近，默认 true
   * @param {number} params.min_amount - 最低成交额均值(10日)，默认 200000000
   * @param {boolean} params.exclude_st - 排除 ST，默认 true
   * @param {boolean} params.exclude_cyb - 排除创业板，默认 true
   * @param {boolean} params.exclude_kcb - 排除科创板，默认 true
   * @param {boolean} params.exclude_bse - 排除北交所，默认 true
   * @param {string} params.sort_field - 排序字段，默认 bb_width
   * @param {string} params.sort_order - 排序方向，默认 asc
   * @param {number} params.page_num - 页码，默认 1
   * @param {number} params.page_size - 每页条数，默认 20
   * @returns {Promise<Object>} - {trade_date, total, page_num, page_size, list}
   */
  getRangePicker (params = {}) {
    return request({
      url: '/stock/daily/range-picker',
      method: 'post',
      data: {
        max_pct_chg_20d: 10.0,
        min_amplitude_20d: 3.0,
        bb_width_max: 0.08,
        rsi_min: 35,
        rsi_max: 65,
        volume_shrink: true,
        near_ma20: true,
        min_amount: 200000000,
        exclude_st: true,
        exclude_cyb: true,
        exclude_kcb: true,
        exclude_bse: true,
        sort_field: 'bb_width',
        sort_order: 'asc',
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 主升浪选股
   * @param {Object} params - 查询参数
   * @param {string} params.trade_date - 交易日期 (YYYY-MM-DD)
   * @param {boolean} params.only_s_level - 仅看硬核S级，默认 false
   * @param {boolean} params.exclude_st - 排除 ST，默认 true
   * @param {boolean} params.exclude_cyb - 排除创业板，默认 true
   * @param {boolean} params.exclude_kcb - 排除科创板，默认 true
   * @param {boolean} params.exclude_bse - 排除北交所，默认 true
   * @param {string} params.sort_field - 排序字段，默认 level
   * @param {string} params.sort_order - 排序方向，默认 desc
   * @param {number} params.page_num - 页码，默认 1
   * @param {number} params.page_size - 每页条数，默认 20
   * @returns {Promise<Object>} - {trade_date, total, page_num, page_size, list}
   */
  getMainwavePicker (params = {}) {
    return request({
      url: '/stock/daily/mainwave-picker',
      method: 'post',
      data: {
        only_s_level: false,
        exclude_st: true,
        exclude_cyb: true,
        exclude_kcb: true,
        exclude_bse: true,
        sort_field: 'level',
        sort_order: 'desc',
        page_num: 1,
        page_size: 20,
        ...params
      }
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
   * @returns {Promise<Object>} - {trade_date, total, success, failed}
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
  /**
   * 按日期同步全部A股日线数据（从API获取并更新数据库）
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {Promise<Object>}
   */
  syncByDate (tradeDate) {
    return request({
      url: `/sync/daily/date/${tradeDate}`,
      method: 'post',
      timeout: 600000
    })
  },

  /**
   * 同步所有股票日线数据
   * @returns {Promise<Object>}
   */
  syncAll () {
    return request({
      url: '/sync/daily',
      method: 'post'
    })
  },

  /**
   * 创建 SSE 实时进度流连接
   * @param {string} tradeDate - 交易日期 (YYYY-MM-DD)
   * @returns {EventSource}
   */
  createSyncStream (tradeDate) {
    // EventSource 不走 webpack devServer proxy，必须直连后端
    const base = process.env.NODE_ENV === 'production'
      ? (process.env.VUE_APP_BASE_API || '/api')
      : 'http://localhost:9000/api'
    return new EventSource(`${base}/sync/daily/date/${tradeDate}/stream`)
  }
}

/**
 * 股票基础信息 API
 */
export const stockBasicApi = {
  /**
   * 分页查询股票基础信息（支持排序）
   * @param {Object} params - 查询参数
   * @param {number} params.pageNum - 页码，默认 1
   * @param {number} params.pageSize - 每页条数，默认 100
   * @param {string} params.sortField - 排序字段：symbol, name, industry, market, area, listDate
   * @param {string} params.sortOrder - 排序方向：asc(升序), desc(降序)
   * @param {string} params.symbol - 股票代码（精确匹配）
   * @param {string} params.name - 股票名称（模糊匹配）
   * @returns {Promise<Object>}
   */
  pageQuery (params = {}) {
    return request({
      url: '/stock/basic/page',
      method: 'post',
      data: {
        page_num: 1,
        page_size: 100,
        sort_field: 'symbol',
        sort_order: 'asc',
        ...params
      }
    })
  },

  /**
   * 获取所有股票基础信息列表（分页）
   * @param {number} pageNum - 页码
   * @param {number} pageSize - 每页条数
   * @returns {Promise<Object>}
   */
  listAll (pageNum = 1, pageSize = 100) {
    return request({
      url: '/stock/basic/list',
      method: 'get',
      params: {
        page_num: pageNum,
        page_size: pageSize
      }
    })
  },

  /**
   * 根据代码获取股票基础信息
   * @param {string} symbol - 股票代码
   * @returns {Promise<Object>}
   */
  getBySymbol (symbol) {
    return request({
      url: `/stock/basic/symbol/${symbol}`,
      method: 'get'
    })
  }
}
