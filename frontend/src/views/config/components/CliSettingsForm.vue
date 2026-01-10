<template>
  <el-form :model="form" label-width="0">
    <el-form-item>
      <el-input
        v-model="form.default_json_config"
        type="textarea"
        :rows="10"
        placeholder='{"env": {}, "permissions": {}}'
      />
      <div class="form-tip">此处配置会合并到 CLI 的配置文件中</div>
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { CliSettings } from '@/types/models'

const props = defineProps<{
  cliType: string
  settings?: CliSettings
}>()

const emit = defineEmits<{
  save: [cliType: string, data: { default_json_config: string }]
}>()

const form = ref({
  default_json_config: '{}'
})

watch(() => props.settings, (settings) => {
  if (settings) {
    form.value = {
      default_json_config: settings.default_json_config
    }
  }
}, { immediate: true })

function handleSave() {
  emit('save', props.cliType, form.value)
}
</script>

<style scoped>
.form-tip {
  margin-top: 5px;
  color: #999;
  font-size: 12px;
}
</style>
