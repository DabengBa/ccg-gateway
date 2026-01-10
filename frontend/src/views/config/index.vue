<template>
  <div class="config-page">
    <el-row :gutter="20">
      <!-- Gateway Settings -->
      <el-col :span="12">
        <el-card>
          <template #header>网关设置</template>
          <el-form :model="gatewayForm" label-width="120px">
            <el-form-item label="调试日志">
              <el-switch v-model="gatewayForm.debug_log" />
              <span class="tip">开启后记录请求/响应详情</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveGateway">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Timeout Settings -->
      <el-col :span="12">
        <el-card>
          <template #header>超时配置</template>
          <el-form :model="timeoutForm" label-width="140px">
            <el-form-item label="流式首字节超时">
              <el-input-number v-model="timeoutForm.stream_first_byte_timeout" :min="1" />
              <span class="unit">秒</span>
            </el-form-item>
            <el-form-item label="流式空闲超时">
              <el-input-number v-model="timeoutForm.stream_idle_timeout" :min="1" />
              <span class="unit">秒</span>
            </el-form-item>
            <el-form-item label="非流式超时">
              <el-input-number v-model="timeoutForm.non_stream_timeout" :min="1" />
              <span class="unit">秒</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveTimeouts">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- CLI Settings -->
    <el-card style="margin-top: 20px">
      <template #header>CLI 配置</template>
      <el-tabs v-model="activeCliTab">
        <el-tab-pane label="ClaudeCode" name="claude_code">
          <CliSettingsForm cli-type="claude_code" :settings="settingsStore.settings?.cli_settings?.claude_code" @save="saveCli" />
        </el-tab-pane>
        <el-tab-pane label="Codex" name="codex">
          <CliSettingsForm cli-type="codex" :settings="settingsStore.settings?.cli_settings?.codex" @save="saveCli" />
        </el-tab-pane>
        <el-tab-pane label="Gemini" name="gemini">
          <CliSettingsForm cli-type="gemini" :settings="settingsStore.settings?.cli_settings?.gemini" @save="saveCli" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '@/stores/settings'
import CliSettingsForm from './components/CliSettingsForm.vue'

const settingsStore = useSettingsStore()
const activeCliTab = ref('claude_code')

const gatewayForm = ref({
  debug_log: false
})

const timeoutForm = ref({
  stream_first_byte_timeout: 30,
  stream_idle_timeout: 60,
  non_stream_timeout: 120
})

watch(() => settingsStore.settings, (settings) => {
  if (settings) {
    gatewayForm.value = { debug_log: settings.gateway.debug_log }
    timeoutForm.value = { ...settings.timeouts }
  }
}, { immediate: true })

async function saveGateway() {
  await settingsStore.updateGateway(gatewayForm.value)
  ElMessage.success('网关设置已保存')
}

async function saveTimeouts() {
  await settingsStore.updateTimeouts(timeoutForm.value)
  ElMessage.success('超时配置已保存')
}

async function saveCli(cliType: string, data: any) {
  await settingsStore.updateCli(cliType, data)
  ElMessage.success('CLI 配置已保存')
}

onMounted(() => {
  settingsStore.fetchSettings()
})
</script>

<style scoped>
.unit {
  margin-left: 10px;
  color: #999;
}
.tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
