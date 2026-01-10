import api from './instance'
import type { Prompt, PromptCreate, PromptUpdate } from '@/types/models'

export const promptsApi = {
  list: () => api.get<Prompt[]>('/prompts'),
  get: (id: number) => api.get<Prompt>(`/prompts/${id}`),
  create: (data: PromptCreate) => api.post<Prompt>('/prompts', data),
  update: (id: number, data: PromptUpdate) => api.put<Prompt>(`/prompts/${id}`, data),
  delete: (id: number) => api.delete(`/prompts/${id}`)
}
