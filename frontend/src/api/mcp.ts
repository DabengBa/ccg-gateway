import api from './instance'
import type { Mcp, McpCreate, McpUpdate } from '@/types/models'

export const mcpApi = {
  list: () => api.get<Mcp[]>('/mcp'),
  get: (id: number) => api.get<Mcp>(`/mcp/${id}`),
  create: (data: McpCreate) => api.post<Mcp>('/mcp', data),
  update: (id: number, data: McpUpdate) => api.put<Mcp>(`/mcp/${id}`, data),
  delete: (id: number) => api.delete(`/mcp/${id}`)
}
