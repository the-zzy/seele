import axios from 'axios'
import { clearVersionedState } from './storage'

const SERVER_VERSION_KEY = 'seele:server_version'

const LEGACY_KEYS = [
  'seele_token',
  'seele_workspace',
  'agent-session-id'
]

export function getClientVersion () {
  return process.env.VUE_APP_VERSION || 'unknown'
}

export async function getServerVersion () {
  const { data } = await axios.get('/api/version', {
    headers: { 'X-Client-Version': getClientVersion() }
  })
  return data.version
}

function clearLegacyKeys () {
  LEGACY_KEYS.forEach(key => localStorage.removeItem(key))
}

export function clearStaleState () {
  clearVersionedState()
  clearLegacyKeys()
}

export function forceReload () {
  window.location.reload(true)
}

export async function checkVersion () {
  const serverVersion = await getServerVersion()
  const localVersion = localStorage.getItem(SERVER_VERSION_KEY)

  if (localVersion && localVersion !== serverVersion) {
    clearStaleState()
    localStorage.setItem(SERVER_VERSION_KEY, serverVersion)
    forceReload()
    return
  }

  localStorage.setItem(SERVER_VERSION_KEY, serverVersion)
}
