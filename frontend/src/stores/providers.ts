import { defineStore } from 'pinia'
import { ref } from 'vue'
import { providersApi } from '@/api/providers'
import type { Provider, ProviderCreate, ProviderUpdate } from '@/types/models'

export const useProviderStore = defineStore('providers', () => {
  const providers = ref<Provider[]>([])
  const loading = ref(false)
  const currentCliType = ref<string>('claude_code')

  async function fetchProviders(cliType?: string) {
    loading.value = true
    try {
      const type = cliType || currentCliType.value
      const { data } = await providersApi.list(type)
      providers.value = data
    } finally {
      loading.value = false
    }
  }

  function setCliType(cliType: string) {
    currentCliType.value = cliType
  }

  async function createProvider(data: ProviderCreate) {
    const { data: provider } = await providersApi.create(data)
    providers.value.push(provider)
    return provider
  }

  async function updateProvider(id: number, data: ProviderUpdate) {
    const { data: provider } = await providersApi.update(id, data)
    const index = providers.value.findIndex(p => p.id === id)
    if (index !== -1) {
      providers.value[index] = provider
    }
    return provider
  }

  async function deleteProvider(id: number) {
    await providersApi.delete(id)
    providers.value = providers.value.filter(p => p.id !== id)
  }

  async function reorderProviders(ids: number[]) {
    await providersApi.reorder(ids)
    await fetchProviders()
  }

  async function resetFailures(id: number) {
    await providersApi.resetFailures(id)
    await fetchProviders()
  }

  async function unblacklist(id: number) {
    await providersApi.unblacklist(id)
    await fetchProviders()
  }

  return {
    providers,
    loading,
    currentCliType,
    fetchProviders,
    setCliType,
    createProvider,
    updateProvider,
    deleteProvider,
    reorderProviders,
    resetFailures,
    unblacklist
  }
})
