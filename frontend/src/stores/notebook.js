import { defineStore } from 'pinia'
import { getNotebooks, createNotebook, deleteNotebook } from '@/api'

export const useNotebookStore = defineStore('notebook', {
  state: () => ({
    notebooks: [],
    currentNotebookId: null,
    loading: false
  }),

  actions: {
    async fetchNotebooks() {
      this.loading = true
      try {
        const res = await getNotebooks()
        // 后端返回的是分页对象，数据在 results 字段里
        const data = res.data.results || res.data
        this.notebooks = Array.isArray(data)
          ? data.filter(n => n && n.id)
          : []
      } finally {
        this.loading = false
      }
    },

    async addNotebook(name) {
      const res = await createNotebook({ name })
      if (res.data && res.data.id) {
        this.notebooks.unshift(res.data)
      }
      return res.data
    },

    async removeNotebook(id) {
      await deleteNotebook(id)
      this.notebooks = this.notebooks.filter(n => n.id !== id)
      if (this.currentNotebookId === id) {
        this.currentNotebookId = null
      }
    },

    setCurrentNotebook(id) {
      this.currentNotebookId = id
    }
  }
})