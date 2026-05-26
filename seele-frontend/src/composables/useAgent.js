import { ref, markRaw } from 'vue'
import { agentApi } from '@/api/agent'

function clone (val) {
  if (val === null || val === undefined) return val
  if (typeof val !== 'object') return val
  try {
    return JSON.parse(JSON.stringify(val))
  } catch {
    return val
  }
}

export function useAgent () {
  const sessionId = ref(localStorage.getItem('agent-session-id') || '')
  const messages = ref([])
  const loading = ref(false)

  const hasSession = () => !!sessionId.value

  async function sendMessage (text, allowWrite = false) {
    const userMsg = { role: 'user', content: text, time: Date.now() }
    messages.value.push(userMsg)
    loading.value = true

    const assistantMsg = {
      role: 'assistant',
      content: '',
      toolCalls: [],
      time: Date.now()
    }
    messages.value.push(assistantMsg)

    try {
      await agentApi.chatStream({
        message: text,
        session_id: sessionId.value || undefined,
        allow_write: allowWrite
      }, (event, data) => {
        if (event === 'thinking') {
          assistantMsg.content = data.message || '正在分析问题...'
        } else if (event === 'tool_start') {
          assistantMsg.toolCalls.push({
            name: data.name,
            arguments: markRaw(clone(data.arguments)),
            result: null,
            loading: true
          })
        } else if (event === 'tool_end') {
          const tc = assistantMsg.toolCalls.find(t => t.name === data.name && t.loading)
          if (tc) {
            tc.result = markRaw(clone(data.result))
            tc.loading = false
          }
        } else if (event === 'content') {
          assistantMsg.content += data.delta
        } else if (event === 'done') {
          if (data.session_id) {
            sessionId.value = data.session_id
            localStorage.setItem('agent-session-id', data.session_id)
          }
          assistantMsg.content = data.reply
          assistantMsg.toolCalls = (data.tool_calls || []).map(tc => ({
            name: tc.name,
            arguments: markRaw(clone(tc.arguments)),
            result: markRaw(clone(tc.result)),
            loading: false
          }))
        } else if (event === 'error') {
          assistantMsg.role = 'error'
          assistantMsg.content = data.message || '请求失败'
        }
      })
    } catch (e) {
      assistantMsg.role = 'error'
      assistantMsg.content = e.message || '请求失败'
    } finally {
      loading.value = false
    }
  }

  function clearSession () {
    if (sessionId.value) {
      agentApi.clearSession(sessionId.value).catch(() => {})
    }
    sessionId.value = ''
    messages.value = []
    localStorage.removeItem('agent-session-id')
  }

  return {
    sessionId,
    messages,
    loading,
    sendMessage,
    clearSession,
    hasSession
  }
}
