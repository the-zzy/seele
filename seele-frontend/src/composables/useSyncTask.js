import { reactive, onUnmounted } from 'vue'
import { syncApi } from '@/api/stock'
import { toast } from '@/composables/useToast'

export function useSyncTask () {
  const syncing = reactive({})
  const progress = reactive({})
  const timers = reactive({})
  const localKeys = new Set()

  function clearPoll (key) {
    if (timers[key]) {
      clearInterval(timers[key])
      delete timers[key]
    }
    localKeys.delete(key)
  }

  function clearAll () {
    localKeys.forEach(clearPoll)
  }

  function startPoll (taskKey, taskId, { interval = 2000, onDone } = {}) {
    clearPoll(taskKey)
    localKeys.add(taskKey)
    progress[taskKey] = { current: 0, total: 0, status: 'running' }

    const doPoll = async () => {
      try {
        const data = await syncApi.getTaskStatus(taskId)
        const p = data?.progress || { current: 0, total: 0 }
        progress[taskKey] = {
          current: p.current || 0,
          total: p.total || 0,
          status: data?.status || 'running'
        }

        if (data?.status === 'success' || data?.status === 'failed') {
          clearPoll(taskKey)
          syncing[taskKey] = false
          if (onDone) onDone(data)
        }
      } catch (err) {
        // 404 表示任务已不存在（超时清理 / 后端重启），应停止轮询并释放按钮
        if (err.response?.status === 404) {
          clearPoll(taskKey)
          syncing[taskKey] = false
          console.warn('任务已不存在，停止轮询:', taskKey)
          return
        }
        console.error('轮询任务状态失败:', err)
      }
    }

    doPoll()
    timers[taskKey] = setInterval(doPoll, interval)
  }

  async function startSync (taskKey, apiCall, {
    confirmMessage,
    confirmAction,
    checkExisting = true,
    existingMatcher,
    interval = 2000,
    onDone
  } = {}) {
    if (syncing[taskKey]) return

    if (checkExisting) {
      try {
        const active = await syncApi.getActiveTasks()
        const tasks = active?.tasks || []
        const existing = existingMatcher
          ? tasks.find(existingMatcher)
          : null
        if (existing) {
          const message = `该任务已有同步正在运行 (${existing.progress?.current || 0}/${existing.progress?.total || 0})，是否继续跟踪？`
          const confirmed = confirmAction ? await confirmAction(message, { type: 'existing', task: existing }) : confirm(message)
          if (confirmed) {
            syncing[taskKey] = true
            startPoll(taskKey, existing.task_id, { interval, onDone })
          }
          return
        }
      } catch (e) {
        console.error('检查活跃任务失败:', e)
      }
    }

    if (confirmMessage) {
      const confirmed = confirmAction ? await confirmAction(confirmMessage, { type: 'start' }) : confirm(confirmMessage)
      if (!confirmed) return
    }

    syncing[taskKey] = true
    try {
      const res = await apiCall()
      const taskId = res?.task_id
      if (taskId) {
        startPoll(taskKey, taskId, { interval, onDone })
      } else {
        syncing[taskKey] = false
        if (onDone) onDone(null)
      }
    } catch (error) {
      toast.error('同步失败: ' + (error.message || '未知错误'))
      syncing[taskKey] = false
    }
  }

  async function restoreTasks (matchers, { interval = 2000, onDone } = {}) {
    try {
      const active = await syncApi.getActiveTasks()
      const tasks = active?.tasks || []
      for (const task of tasks) {
        for (const matcher of matchers) {
          const key = matcher(task)
          if (key) {
            syncing[key] = true
            progress[key] = {
              current: task.progress?.current || 0,
              total: task.progress?.total || 0,
              status: 'running'
            }
            startPoll(key, task.task_id, { interval, onDone })
            break
          }
        }
      }
    } catch (e) {
      console.error('恢复同步任务失败:', e)
    }
  }

  onUnmounted(() => clearAll())

  return {
    syncing,
    progress,
    clearPoll,
    clearAll,
    startPoll,
    startSync,
    restoreTasks
  }
}
