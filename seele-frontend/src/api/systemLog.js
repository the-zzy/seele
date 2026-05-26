import request from '@/utils/request'

export const systemLogApi = {
  getErrorLogs: (params) => request({ url: '/system/logs/errors', method: 'get', params }),
  getOperationLogs: (params) => request({ url: '/system/logs/operations', method: 'get', params }),
  getOverview: () => request({ url: '/system/logs/overview', method: 'get' })
}
