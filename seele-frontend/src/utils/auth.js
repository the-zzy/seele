const TOKEN_KEY = 'seele_token'

let authRequiredCallback = null

export function getToken () {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken (token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken () {
  localStorage.removeItem(TOKEN_KEY)
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
