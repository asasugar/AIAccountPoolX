import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const platformApi = {
  list: () => api.get('/platforms'),
  get: (id: string) => api.get(`/platforms/${id}`),
  configFields: (id: string) => api.get(`/platforms/${id}/config-fields`),
}

export const taskApi = {
  start: (count: number, interval: number, concurrency = 1, platform = 'openai') =>
    api.post('/task/start', { count, interval, concurrency }, { params: { platform } }),
  stop: (platform = 'openai') =>
    api.post('/task/stop', null, { params: { platform } }),
  status: (platform = 'openai') =>
    api.get('/task/status', { params: { platform } }),
  reset: (platform = 'openai') =>
    api.post('/task/reset', null, { params: { platform } }),
}

export const tokenApi = {
  list: (params?: { platform?: string; search?: string; page?: number; page_size?: number; include_newapi_channel_id?: boolean }) =>
    api.get('/tokens', { params }),
  delete: (id: string, platform = '') =>
    api.delete(`/tokens/${id}`, { params: { platform } }),
  export: (platform = '') =>
    api.get('/tokens/export', { params: { platform } }),
  acquire: (platform = 'openai') =>
    api.post('/tokens/acquire', null, { params: { platform } }),
  release: (tokenId: string, success = true, platform = '') =>
    api.post('/tokens/release', { token_id: tokenId, success, platform }),
  stats: (platform = '') =>
    api.get('/tokens/stats', { params: { platform } }),
  getQuota: (id: string, platform = '') =>
    api.get(`/tokens/${id}/quota`, { params: { platform } }),
  refreshQuota: (id: string, platform = '') =>
    api.post(`/tokens/${id}/quota`, null, { params: { platform } }),
  refreshToken: (id: string, platform = '') =>
    api.post(`/tokens/${id}/refresh`, null, { params: { platform } }),
  batchDelete: (ids: string[], platform = '') =>
    api.post('/tokens/batch-delete', { ids }, { params: { platform } }),
}

export const configApi = {
  get: () => api.get('/config'),
  update: (cfg: Record<string, any>) => api.put('/config', cfg),
}

export const statsApi = {
  get: (platform = '') => api.get('/stats', { params: { platform } }),
}

export const newapiApi = {
  syncStatus: () => api.get('/newapi/sync-status'),
  sync: () => api.post('/newapi/sync'),
  channels: () => api.get('/newapi/channels'),
  testChannel: (channelId: number) => api.get(`/newapi/channel/test/${channelId}`),
  deleteChannel: (channelId: number) => api.delete(`/newapi/channel/${channelId}`),
  batchDeleteChannels: (ids: number[]) => api.post('/newapi/channel/batch', { ids }),
  updateChannel: (channelId: number, tokenId: string, platform = '') =>
    api.put('/newapi/channel', { channel_id: channelId, token_id: tokenId, platform }),
}

export const accountApi = {
  list: (params?: {
    platform?: string
    search?: string
    status?: string
    page?: number
    page_size?: number
    include_password?: boolean
  }) => api.get('/accounts', { params }),
  get: (id: number, includePassword = false) =>
    api.get(`/accounts/${id}`, { params: { include_password: includePassword } }),
  getToken: (id: number) => api.get(`/accounts/${id}/token`),
  create: (data: {
    platform?: string
    email: string
    password?: string
    username?: string
    first_name?: string
    last_name?: string
    birth_year?: number
    birth_month?: number
    birth_day?: number
  }) => api.post('/accounts', data),
  update: (id: number, data: Record<string, any>) => api.put(`/accounts/${id}`, data),
  delete: (id: number) => api.delete(`/accounts/${id}`),
  stats: (platform = '') => api.get('/accounts/stats/summary', { params: { platform } }),
}

export function createLogWebSocket(onMessage: (data: any) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/logs`)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch {}
  }
  return ws
}
