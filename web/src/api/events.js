import axios from 'axios'

const BASE = '/api'

const api = axios.create({ baseURL: BASE })

api.interceptors.response.use(
  r => r,
  err => {
    console.error('API error:', err)
    return Promise.reject(err)
  }
)

export const eventApi = {
  list: (start, end) => start && end ? api.get('/events', { params: { start, end } }).then(r => r.data) : api.get('/events').then(r => r.data),

  tree: () => api.get('/events/tree').then(r => r.data),

  create: (data) => api.post('/events', data).then(r => r.data),

  update: (id, data) => api.put(`/events/${id}`, data).then(r => r.data),

  delete: (id) => api.delete(`/events/${id}`).then(r => r.data),

  checkin: (id, date) => api.post(`/habits/${id}/checkin`, null, { params: { date } }).then(r => r.data),

  sync: (since) => api.get('/sync', { params: since ? { since } : {} }).then(r => r.data),

  health: () => api.get('/health').then(r => r.data).catch(() => null)
}

export default api
