/**
 * 格式化日期
 * @param {string} dateStr - 日期字符串
 * @returns {string}
 */
export function formatDate (dateStr) {
  if (!dateStr) return '-'
  return dateStr
}

/**
 * 格式化数字，保留指定位数小数
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数，默认 2
 * @returns {string}
 */
export function formatNumber (num, decimals = 2) {
  if (num === null || num === undefined) return '-'
  return parseFloat(num).toFixed(decimals)
}

/**
 * 格式化涨跌幅
 * @param {number} pctChg - 涨跌幅数值
 * @returns {string}
 */
export function formatPctChg (pctChg) {
  if (pctChg === null || pctChg === undefined) return '-'
  const value = parseFloat(pctChg)
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%'
}

/**
 * 格式化成交量
 * @param {number} volume - 成交量
 * @returns {string}
 */
export function formatVolume (volume) {
  if (!volume) return '-'
  if (volume >= 100000000) {
    return (volume / 100000000).toFixed(2) + '亿'
  } else if (volume >= 10000) {
    return (volume / 10000).toFixed(2) + '万'
  }
  return volume.toString()
}

/**
 * 格式化成交额
 * @param {number} amount - 成交额
 * @returns {string}
 */
export function formatAmount (amount) {
  if (!amount) return '-'
  const value = parseFloat(amount)
  if (value >= 100000000) {
    return (value / 100000000).toFixed(2) + '亿'
  } else if (value >= 10000) {
    return (value / 10000).toFixed(2) + '万'
  }
  return value.toFixed(2)
}

/**
 * 获取价格样式类（基于涨跌幅）
 * @param {number} price - 当前价格
 * @param {number} pctChg - 涨跌幅
 * @returns {string} 'up' | 'down' | ''
 */
export function getPriceClass (price, pctChg) {
  if (!price || pctChg === null || pctChg === undefined) return ''
  const value = parseFloat(pctChg)
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return ''
}

/**
 * 格式化换手率
 * @param {number} turnover - 换手率
 * @returns {string}
 */
export function formatTurnover (turnover) {
  if (turnover === null || turnover === undefined) return '-'
  return (parseFloat(turnover) * 100).toFixed(2) + '%'
}
