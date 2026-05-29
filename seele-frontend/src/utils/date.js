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
 * 获取最近交易日（若今天是周末则回退到周五）
 * @returns {string}
 */
export function getLatestWeekday () {
  const d = new Date()
  const day = d.getDay()
  if (day === 0) {
    d.setDate(d.getDate() - 2)
  } else if (day === 6) {
    d.setDate(d.getDate() - 1)
  }
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const dayStr = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${dayStr}`
}
