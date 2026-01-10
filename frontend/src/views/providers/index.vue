<template>
  <div class="providers-page">
    <el-tabs v-model="activeCliType" @tab-change="handleCliTypeChange">
      <el-tab-pane label="Claude Code" name="claude_code" />
      <el-tab-pane label="Codex" name="codex" />
      <el-tab-pane label="Gemini" name="gemini" />
    </el-tabs>

    <div class="page-header">
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加服务商
      </el-button>
    </div>

    <el-card v-loading="providerStore.loading">
      <template v-if="providerStore.providers.length === 0">
        <el-empty description="暂无服务商" />
      </template>
      <draggable
        v-else
        v-model="providerStore.providers"
        item-key="id"
        handle=".drag-handle"
        @end="handleDragEnd"
      >
        <template #item="{ element }">
          <div class="provider-item">
            <div class="drag-handle" aria-label="拖拽排序">
              <el-icon><Rank /></el-icon>
            </div>
            <div class="provider-info">
              <div class="provider-name">
                {{ element.name }}
                <el-tag v-if="element.is_blacklisted" type="danger" size="small">已拉黑</el-tag>
                <el-tag v-else-if="!element.enabled" type="info" size="small">已禁用</el-tag>
              </div>
              <div class="provider-url">{{ element.base_url }}</div>
            </div>
            <div class="provider-stats">
              <span>失败: {{ element.consecutive_failures }}/{{ element.failure_threshold }}</span>
            </div>
            <div class="provider-actions">
              <el-switch
                v-model="element.enabled"
                @change="handleToggle(element)"
              />
              <el-button size="small" @click="handleEdit(element)">编辑</el-button>
              <el-dropdown @command="handleCommand($event, element)">
                <el-button size="small">
                  更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="reset">重置失败计数</el-dropdown-item>
                    <el-dropdown-item v-if="element.is_blacklisted" command="unblacklist">解除拉黑</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </template>
      </draggable>
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="showDialog"
      :title="editingProvider ? '编辑服务商' : '添加服务商'"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="服务商名称" />
        </el-form-item>
        <el-form-item label="Base URL" required>
          <el-input v-model="form.base_url" placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item :label="activeCliType === 'claude_code' ? 'API Token' : 'API Key'" required>
          <el-input v-model="form.api_key" :placeholder="activeCliType === 'claude_code' ? 'API Token' : 'API Key'" />
        </el-form-item>
        <el-form-item label="失败阈值">
          <el-input-number v-model="form.failure_threshold" :min="1" :max="100" />
          <span class="form-tip">连续失败次数达到此值后拉黑</span>
        </el-form-item>
        <el-form-item label="拉黑时长(分钟)">
          <el-input-number v-model="form.blacklist_minutes" :min="0" :max="1440" />
        </el-form-item>

        <template v-if="activeCliType === 'claude_code'">
          <el-divider>模型转发配置</el-divider>
          <el-form-item label="主模型">
          <el-input v-model="form.model_primary" placeholder="留空则不转发" />
        </el-form-item>
        <el-form-item label="推理模型">
          <el-input v-model="form.model_reasoning" placeholder="留空则不转发" />
        </el-form-item>
        <el-form-item label="Haiku 模型">
          <el-input v-model="form.model_haiku" placeholder="留空则不转发" />
        </el-form-item>
        <el-form-item label="Sonnet 模型">
          <el-input v-model="form.model_sonnet" placeholder="留空则不转发" />
        </el-form-item>
        <el-form-item label="Opus 模型">
            <el-input v-model="form.model_opus" placeholder="留空则不转发" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import { useProviderStore } from '@/stores/providers'
import type { Provider, ModelMap, CliType } from '@/types/models'

const providerStore = useProviderStore()

const activeCliType = ref<CliType>('claude_code')
const showAddDialog = ref(false)
const editingProvider = ref<Provider | null>(null)

const showDialog = computed({
  get: () => showAddDialog.value || !!editingProvider.value,
  set: (val) => {
    if (!val) {
      showAddDialog.value = false
      editingProvider.value = null
    }
  }
})

const form = ref({
  name: '',
  base_url: '',
  api_key: '',
  failure_threshold: 3,
  blacklist_minutes: 10,
  model_primary: '',
  model_reasoning: '',
  model_haiku: '',
  model_sonnet: '',
  model_opus: ''
})

function resetForm() {
  form.value = {
    name: '',
    base_url: '',
    api_key: '',
    failure_threshold: 3,
    blacklist_minutes: 10,
    model_primary: '',
    model_reasoning: '',
    model_haiku: '',
    model_sonnet: '',
    model_opus: ''
  }
}

function handleCliTypeChange(cliType: string) {
  providerStore.setCliType(cliType)
  providerStore.fetchProviders(cliType)
}

function handleEdit(provider: Provider) {
  editingProvider.value = provider
  form.value = {
    name: provider.name,
    base_url: provider.base_url,
    api_key: provider.api_key,
    failure_threshold: provider.failure_threshold,
    blacklist_minutes: provider.blacklist_minutes,
    model_primary: provider.model_maps.find(m => m.model_role === 'primary')?.target_model || '',
    model_reasoning: provider.model_maps.find(m => m.model_role === 'reasoning')?.target_model || '',
    model_haiku: provider.model_maps.find(m => m.model_role === 'haiku')?.target_model || '',
    model_sonnet: provider.model_maps.find(m => m.model_role === 'sonnet')?.target_model || '',
    model_opus: provider.model_maps.find(m => m.model_role === 'opus')?.target_model || ''
  }
}

function buildModelMaps(): ModelMap[] {
  if (activeCliType.value !== 'claude_code') {
    return []
  }
  const maps: ModelMap[] = []
  if (form.value.model_primary) {
    maps.push({ model_role: 'primary', target_model: form.value.model_primary, enabled: true })
  }
  if (form.value.model_reasoning) {
    maps.push({ model_role: 'reasoning', target_model: form.value.model_reasoning, enabled: true })
  }
  if (form.value.model_haiku) {
    maps.push({ model_role: 'haiku', target_model: form.value.model_haiku, enabled: true })
  }
  if (form.value.model_sonnet) {
    maps.push({ model_role: 'sonnet', target_model: form.value.model_sonnet, enabled: true })
  }
  if (form.value.model_opus) {
    maps.push({ model_role: 'opus', target_model: form.value.model_opus, enabled: true })
  }
  return maps
}

async function handleSave() {
  const data = {
    cli_type: activeCliType.value,
    name: form.value.name,
    base_url: form.value.base_url,
    api_key: form.value.api_key,
    failure_threshold: form.value.failure_threshold,
    blacklist_minutes: form.value.blacklist_minutes,
    model_maps: buildModelMaps()
  }

  try {
    if (editingProvider.value) {
      await providerStore.updateProvider(editingProvider.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await providerStore.createProvider(data)
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    resetForm()
    providerStore.fetchProviders(activeCliType.value)
  } catch {
    // error handled by interceptor
  }
}

async function handleToggle(provider: Provider) {
  try {
    await providerStore.updateProvider(provider.id, { enabled: provider.enabled })
    ElMessage.success(provider.enabled ? '已启用' : '已禁用')
  } catch {
    provider.enabled = !provider.enabled
  }
}

async function handleDragEnd() {
  const ids = providerStore.providers.map(p => p.id)
  await providerStore.reorderProviders(ids)
  ElMessage.success('排序已保存')
}

async function handleCommand(command: string, provider: Provider) {
  if (command === 'reset') {
    await providerStore.resetFailures(provider.id)
    ElMessage.success('已重置')
  } else if (command === 'unblacklist') {
    await providerStore.unblacklist(provider.id)
    ElMessage.success('已解除拉黑')
  } else if (command === 'delete') {
    await ElMessageBox.confirm('确定删除该服务商?', '确认')
    await providerStore.deleteProvider(provider.id)
    ElMessage.success('已删除')
  }
}

onMounted(() => {
  providerStore.fetchProviders(activeCliType.value)
})
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}

.provider-item {
  display: flex;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.provider-item:last-child {
  border-bottom: none;
}

.drag-handle {
  cursor: move;
  padding: 10px;
  color: var(--el-text-color-secondary);
}

.provider-info {
  flex: 1;
  margin-left: 10px;
}

.provider-name {
  font-weight: bold;
  margin-bottom: 5px;
}

.provider-url {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.provider-stats {
  display: flex;
  gap: 20px;
  margin-right: 20px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.provider-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.form-tip {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
