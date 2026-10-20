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

// ========== 用户 API ==========
export const getUserProfile = () => axios.get('/api/v1/auth/profile/')
export const getCurrentUser = () => axios.get('/api/v1/auth/me/')
export const updateProfile = (formData) =>
  axios.patch('/api/v1/auth/me/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

// ========== 测验 API ==========
export const generateQuiz = (noteId, questionCount = 5, idempotencyKey = '') =>
  axios.post(
    `/api/v1/quizzes/generate/${noteId}/`,
    { question_count: questionCount },
    idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : undefined
  )

export const generateAdaptiveQuiz = (payload) =>
  axios.post('/api/v1/quizzes/adaptive/', payload)

export const getMastery = () => axios.get('/api/v1/learning/mastery/')
export const getLearningCurve = () => axios.get('/api/v1/learning/curve/')
export const getReviewDue = () => axios.get('/api/v1/learning/review/due/')
export const startReviewPractice = (count = 10) =>
  axios.post('/api/v1/learning/review/practice/', { count })

export const getQuizStatus = (quizId) =>
  axios.get(`/api/v1/quizzes/${quizId}/status/`)

export const cancelQuizGeneration = (quizId) =>
  axios.post(`/api/v1/quizzes/${quizId}/cancel-delete/`)

export const deleteQuiz = (quizId) =>
  axios.post(`/api/v1/quizzes/${quizId}/delete/`)

export const getQuizQuestions = (quizId) =>
  axios.get(`/api/v1/quizzes/${quizId}/questions/`)

export const submitQuizAnswers = (quizId, answers, idempotencyKey = '') =>
  axios.post(
    `/api/v1/quizzes/${quizId}/attempt/`,
    { answers },
    idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : undefined
  )

export const getQuizAttempts = (quizId) =>
  axios.get(`/api/v1/quizzes/${quizId}/attempts/`)

export const getQuizReview = (quizId) =>
  axios.get(`/api/v1/quizzes/${quizId}/review/`)

export const getQuizHistory = () =>
  axios.get('/api/v1/quizzes/')

// ========== 错题本 API ==========
export const getWrongQuestions = (params) =>
  axios.get('/api/v1/wrong-questions/list/', { params })

export const rePracticeWrong = (data) =>
  axios.post('/api/v1/wrong-questions/re-practice/', data)

export const getWrongQuestionTags = () =>
  axios.get('/api/v1/wrong-questions/tags/')

export const removeWrongQuestion = (wrongId) =>
  axios.delete(`/api/v1/wrong-questions/${wrongId}/remove/`)

// ========== 互操作 API ==========
export const importNotes = (formData) =>
  axios.post('/api/v1/io/import/', formData)

export const exportQuestions = () =>
  axios.get('/api/v1/io/export/', { responseType: 'blob' })