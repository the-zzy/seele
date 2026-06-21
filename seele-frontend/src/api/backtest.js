import request from '@/utils/request'

/**
 * 回测 API
 */
export const backtestApi = {
  /**
   * 创建回测
   * @param {Object} data
   * @param {string} data.start_date - 开始日期 YYYY-MM-DD
   * @param {string} [data.end_date] - 结束日期 YYYY-MM-DD
   * @param {number} [data.initial_capital] - 初始资金
   * @param {string} [data.ai_model] - AI 模型
   */
  create (data) {
    return request({
      url: '/backtest',
      method: 'post',
      data
    })
  },

  /**
   * 回测列表
   */
  getList (params = {}) {
    return request({
      url: '/backtest',
      method: 'get',
      params: {
        page_num: 1,
        page_size: 20,
        ...params
      }
    })
  },

  /**
   * 获取回测详情
   */
  getById (runId) {
    return request({
      url: `/backtest/${runId}`,
      method: 'get'
    })
  },

  /**
   * 手动执行下一天
   */
  step (runId) {
    return request({
      url: `/backtest/${runId}/step`,
      method: 'post'
    })
  },

  /**
   * 异步执行下一天
   */
  stepAsync (runId) {
    return request({
      url: `/backtest/${runId}/step-async`,
      method: 'post'
    })
  },

  /**
   * 自动运行到结束日期
   */
  auto (runId, endDate) {
    return request({
      url: `/backtest/${runId}/auto`,
      method: 'post',
      params: endDate ? { end_date: endDate } : {}
    })
  },

  /**
   * 查询自动运行任务状态
   */
  getTaskStatus (taskId) {
    return request({
      url: `/backtest/task/${taskId}`,
      method: 'get'
    })
  },

  /**
   * 查询指定回测是否有正在执行的后台任务
   */
  getRunningTask (runId) {
    return request({
      url: `/backtest/${runId}/running-task`,
      method: 'get'
    })
  },

  /**
   * 获取交易记录
   */
  getTrades (runId, params = {}) {
    return request({
      url: `/backtest/${runId}/trades`,
      method: 'get',
      params: {
        page_num: 1,
        page_size: 100,
        ...params
      }
    })
  },

  /**
   * 获取每日快照
   */
  getSnapshots (runId, params = {}) {
    return request({
      url: `/backtest/${runId}/snapshots`,
      method: 'get',
      params: {
        page_num: 1,
        page_size: 100,
        ...params
      }
    })
  },

  /**
   * 获取 AI 决策日志
   */
  getDecisions (runId, params = {}) {
    return request({
      url: `/backtest/${runId}/decisions`,
      method: 'get',
      params: {
        page_num: 1,
        page_size: 100,
        ...params
      }
    })
  },

  /**
   * 删除回测
   */
  delete (runId) {
    return request({
      url: `/backtest/${runId}`,
      method: 'delete'
    })
  },

  /**
   * 撤回一天
   */
  revert (runId) {
    return request({
      url: `/backtest/${runId}/revert`,
      method: 'post'
    })
  },

  /**
   * 批量删除回测
   * @param {number[]} [runIds] - 指定要删除的回测 ID 列表，不传则清空全部
   */
  batchDelete (runIds = null) {
    return request({
      url: '/backtest/batch-delete',
      method: 'post',
      data: runIds ? { run_ids: runIds } : {}
    })
  }
}
