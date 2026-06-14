const APP_VERSION = process.env.VUE_APP_VERSION || 'unknown'

function versionedKey (key) {
  return `seele:${APP_VERSION}:${key}`
}

export function getItem (key, options = {}) {
  const { versioned = true } = options
  const storageKey = versioned ? versionedKey(key) : key
  return localStorage.getItem(storageKey)
}

export function setItem (key, value, options = {}) {
  const { versioned = true } = options
  const storageKey = versioned ? versionedKey(key) : key
  localStorage.setItem(storageKey, value)
}

export function removeItem (key, options = {}) {
  const { versioned = true } = options
  const storageKey = versioned ? versionedKey(key) : key
  localStorage.removeItem(storageKey)
}

export function clearVersionedState () {
  const currentPrefix = `seele:${APP_VERSION}:`
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i)
    if (key && key.startsWith('seele:') && !key.startsWith(currentPrefix)) {
      localStorage.removeItem(key)
    }
  }
}
