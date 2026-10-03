import { defineStore } from 'pinia'
import { tokenStorage } from '@/utils/token'
import { isHrAdmin, isSuperuser } from '@/utils/permission'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: tokenStorage.get(),
    user: null,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    isSuperuser: (state) => isSuperuser(state.user),
    isHrAdmin: (state) => isHrAdmin(state.user),
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      tokenStorage.set(token)
    },
    setUser(user) {
      this.user = user
    },
    logout() {
      this.token = ''
      this.user = null
      tokenStorage.clear()
    },
  },
})
