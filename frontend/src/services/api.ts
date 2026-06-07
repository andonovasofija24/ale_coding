import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ale_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ale_token')
      localStorage.removeItem('ale_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post('/auth/register', data).then((r) => r.data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data).then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
}

// Tasks (student)
export const tasksApi = {
  list: () => api.get('/tasks').then((r) => r.data),
  get: (id: string) => api.get(`/tasks/${id}`).then((r) => r.data),
}

// Sessions
export const sessionsApi = {
  start: (taskId: string) => api.post('/sessions', { task_id: taskId }).then((r) => r.data),
  getForTask: (taskId: string) => api.get(`/sessions/task/${taskId}`).then((r) => r.data),
  get: (id: string) => api.get(`/sessions/${id}`).then((r) => r.data),
  saveCode: (sessionId: string, code: string) =>
    api.patch(`/sessions/${sessionId}/code`, { code }).then((r) => r.data),
  checkStep: (sessionId: string, code: string) =>
    api.post(`/sessions/${sessionId}/check-step`, { code }).then((r) => r.data),
  getHint: (sessionId: string, code: string) =>
    api.post(`/sessions/${sessionId}/hint`, { code }).then((r) => r.data),
  runTests: (taskId: string, code: string) =>
    api.post(`/sessions/run-tests/${taskId}`, { code }).then((r) => r.data),
  explainErrors: (taskId: string, code: string, errors: string[]) =>
    api.post(`/sessions/run-tests/${taskId}/explain`, { code, errors }).then((r) => r.data),
  startNew: (taskId: string) =>
    api.post('/sessions', { task_id: taskId, force_new: true }).then((r) => r.data),
}

// Admin
export const adminApi = {
  listTasks: () => api.get('/admin/tasks').then((r) => r.data),
  getTask: (id: string) => api.get(`/admin/tasks/${id}`).then((r) => r.data),
  createTask: (data: object) => api.post('/admin/tasks', data).then((r) => r.data),
  updateTask: (id: string, data: object) => api.put(`/admin/tasks/${id}`, data).then((r) => r.data),
  deleteTask: (id: string) => api.delete(`/admin/tasks/${id}`),
  addTestCase: (taskId: string, data: object) =>
    api.post(`/admin/tasks/${taskId}/test-cases`, data).then((r) => r.data),
  deleteTestCase: (taskId: string, tcId: string) =>
    api.delete(`/admin/tasks/${taskId}/test-cases/${tcId}`),
}
