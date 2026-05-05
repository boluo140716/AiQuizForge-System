import axios from 'axios'

// ========== 笔记本 API ==========
export const getNotebooks = () => axios.get('/api/v1/notebooks/')
export const createNotebook = (data) => axios.post('/api/v1/notebooks/', data)
export const updateNotebook = (id, data) => axios.put(`/api/v1/notebooks/${id}/`, data)
export const deleteNotebook = (id) => axios.delete(`/api/v1/notebooks/${id}/`)

// ========== 笔记 API ==========
export const getNotes = (params) => axios.get('/api/v1/notes/', { params })
export const getNoteDetail = (id) => axios.get(`/api/v1/notes/${id}/`)
export const createNote = (data) => axios.post('/api/v1/notes/', data)
export const updateNote = (id, data) => axios.put(`/api/v1/notes/${id}/`, data)
export const deleteNote = (id) => axios.delete(`/api/v1/notes/${id}/`)