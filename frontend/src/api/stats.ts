import api from './instance'
import type { DailyStats, ProviderStats } from '@/types/models'

export const statsApi = {
  getDaily: (params?: { start_date?: string; end_date?: string; cli_type?: string; provider_id?: number }) =>
    api.get<DailyStats[]>('/stats/daily', { params }),
  getProviders: (params?: { start_date?: string; end_date?: string }) =>
    api.get<ProviderStats[]>('/stats/providers', { params })
}
