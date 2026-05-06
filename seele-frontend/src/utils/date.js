import { stockDailyApi } from '@/api/stock'

/**
 * 获取今日日期，格式 YYYY-MM-DD（按本地时区，不会因 UTC 偏移取到昨天）
 * @returns {string}
 */
export function getDefaultDate () {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * 从后端获取最近交易日，失败则回退到本地今日
 * @returns {Promise<string>}
 */
export async function getLatestTradeDate () {
  try {
    const dates = await stockDailyApi.getTradeDates()
    if (Array.isArray(dates) && dates.length > 0) {
      return dates[0]
    }
  } catch (error) {
    console.error('获取最近交易日失败:', error)
  }
  return getDefaultDate()
}
