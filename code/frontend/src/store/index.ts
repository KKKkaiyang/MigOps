import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>('')
  const username = ref<string>('')

  function setUser(name: string, tk: string) {
    username.value = name
    token.value = tk
  }

  return { token, username, setUser }
})
