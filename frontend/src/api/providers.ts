import api from './instance'
import type { Provider, ProviderCreate, ProviderUpdate } from '@/types/models'

export const providersApi = {
  list: (cliType?: string) => api.get<Provider[]>('/providers', { params: cliType ? { cli_type: cliType } : {} }),
  get: (id: number) => api.get<Provider>(`/providers/${id}`),
  create: (data: ProviderCreate) => api.post<Provider>('/providers', data),
  update: (id: number, data: ProviderUpdate) => api.put<Provider>(`/providers/${id}`, data),
  delete: (id: number) => api.delete(`/providers/${id}`),
  reorder: (ids: number[]) => api.post('/providers/reorder', { ids }),
  resetFailures: (id: number) => api.post(`/providers/${id}/reset-failures`),
  unblacklist: (id: number) => api.post(`/providers/${id}/unblacklist`)
}
