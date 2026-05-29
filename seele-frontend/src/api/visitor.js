import request from '@/utils/request'

export const visitorApi = {
  track (data) {
    return request({
      url: '/visitor/track',
      method: 'post',
      data
    })
  },

  getLogs (params = {}) {
    return request({
      url: '/visitor/logs',
      method: 'get',
      params
    })
  }
}
