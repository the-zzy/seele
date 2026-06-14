import request, { baseURL } from '@/utils/request'
import { getToken } from '@/utils/auth'

export const agentApi = {
  chatStream (data, onEvent) {
    const headers = { 'Content-Type': 'application/json' }
    const token = getToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    return fetch(`${baseURL}/agent/chat/stream`, {
      method: 'post',
      headers,
      body: JSON.stringify(data)
    }).then(async (response) => {
      if (!response.ok) {
        const err = await response.text()
        throw new Error(err || `HTTP ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const events = buffer.split('\n\n')
        buffer = events.pop() // 保留未完整接收的部分

        for (const eventText of events) {
          const lines = eventText.trim().split('\n')
          let event = 'message'
          let data = ''
          for (const line of lines) {
            if (line.startsWith('event:')) event = line.slice(6).trim()
            else if (line.startsWith('data:')) data = line.slice(5).trim()
          }
          if (data) {
            try {
              onEvent(event, JSON.parse(data))
            } catch {
              // 忽略非 JSON 数据
            }
          }
        }
      }
    })
  },

  clearSession (sessionId) {
    return request({
      url: `/agent/session/${sessionId}`,
      method: 'delete'
    })
  }
}
