// JWT 存取与认证头构造（注入式 storage，便于单测；默认用 localStorage）。

export const TOKEN_KEY = 'hra_token'

export function createTokenStorage(storage) {
  return {
    get() {
      try {
        return storage.getItem(TOKEN_KEY) || ''
      } catch {
        return ''
      }
    },
    set(token) {
      try {
        storage.setItem(TOKEN_KEY, token)
      } catch {
        /* ignore quota/security errors */
      }
    },
    clear() {
      try {
        storage.removeItem(TOKEN_KEY)
      } catch {
        /* ignore */
      }
    },
  }
}

export function buildAuthHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const tokenStorage = createTokenStorage(globalThis.localStorage)
