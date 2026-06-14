import { getItem, removeItem, setItem } from './storage'

const TOKEN_KEY = 'token'

let authRequiredCallback = null

export function getToken () {
  return getItem(TOKEN_KEY)
}

export function setToken (token) {
  setItem(TOKEN_KEY, token)
}

export function removeToken () {
  removeItem(TOKEN_KEY)
}

export function isLoggedIn () {
  return !!getToken()
}

export function onAuthRequired (cb) {
  authRequiredCallback = cb
}

export function requireAuth () {
  if (authRequiredCallback) {
    authRequiredCallback()
  }
}
