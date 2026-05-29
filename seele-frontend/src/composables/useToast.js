import { reactive } from 'vue'

const state = reactive({
  list: []
})

let idCounter = 0

function add (message, type = 'info', duration = 3000) {
  const id = ++idCounter
  const item = { id, message, type, duration }
  state.list.push(item)

  // 最多保留 5 条
  if (state.list.length > 5) {
    state.list.shift()
  }

  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
  return id
}

function remove (id) {
  const idx = state.list.findIndex(i => i.id === id)
  if (idx > -1) {
    state.list.splice(idx, 1)
  }
}

function clear () {
  state.list = []
}

export const toast = {
  list: state.list,
  success: (msg, duration) => add(msg, 'success', duration),
  error: (msg, duration) => add(msg, 'error', duration),
  warning: (msg, duration) => add(msg, 'warning', duration),
  info: (msg, duration) => add(msg, 'info', duration),
  add,
  remove,
  clear
}

export function useToast () {
  return toast
}

export default toast
