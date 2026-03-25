<template>
  <el-dialog
    v-model="visible"
    title="系统配置"
    width="760px"
    @close="$emit('close')"
    :close-on-click-modal="false"
    align-center
    append-to-body
    class="config-dialog"
  >
    <el-form :model="form" label-width="120px" label-position="left" class="h-[60vh] overflow-y-auto">

      <div class="relative py-2">
        <el-divider content-position="left">
          <span class="flex items-center gap-2 text-indigo-400 font-medium text-xs uppercase tracking-wider">
            <el-icon><Message /></el-icon> 邮箱设置
          </span>
        </el-divider>
      </div>

      <el-form-item label="当前预设">
        <div class="flex gap-2 w-full">
          <el-select v-model="form.active_email_preset" @change="onPresetChange" class="flex-1">
            <el-option
              v-for="(p, i) in form.email_presets"
              :key="i"
              :label="p.name || `预设 ${i + 1}`"
              :value="i"
            />
          </el-select>
          <el-input
            v-model="form.email_presets[form.active_email_preset]!.name"
            placeholder="预设名称"
            class="w-32"
          />
        </div>
      </el-form-item>

      <el-form-item label="邮箱域名">
        <el-input v-model="form.domain" placeholder="example.com" />
      </el-form-item>
      <el-form-item v-if="currentPresetType !== 'tempmail_lol'" label="IMAP 主机">
        <div class="flex gap-2 w-full">
          <el-input v-model="form.imap_host" placeholder="imap.example.com" class="flex-1" />
          <el-input-number v-model="form.imap_port" :min="1" :max="65535" controls-position="right" class="w-28" />
        </div>
      </el-form-item>
      <el-form-item v-if="currentPresetType !== 'tempmail_lol'" label="IMAP 用户名">
        <el-input v-model="form.imap_user" placeholder="user@example.com" />
      </el-form-item>
      <el-form-item v-if="currentPresetType !== 'tempmail_lol'" label="IMAP 密码">
        <el-input v-model="form.imap_pass" type="password" show-password placeholder="••••••••" />
      </el-form-item>
      <el-form-item v-if="currentPresetType === 'tempmail_lol'" label="Tempmail API">
        <el-input
          :model-value="form.email_presets[form.active_email_preset]?.tempmail_base_url || 'https://api.tempmail.lol/v2'"
          @update:model-value="onTempmailBaseUrlChange"
          placeholder="https://api.tempmail.lol/v2"
        />
      </el-form-item>

      <div class="relative py-2 mt-4">
        <el-divider content-position="left">
          <span class="flex items-center gap-2 text-emerald-400 font-medium text-xs uppercase tracking-wider">
            <el-icon><Cpu /></el-icon> 注册设置
          </span>
        </el-divider>
      </div>

      <el-form-item label="邮箱前缀">
        <el-input v-model="form.email_prefix" placeholder="auto" />
        <div class="text-[10px] text-slate-500 mt-1 leading-tight">Prefix for generated emails (e.g. prefix.uuid@domain)</div>
      </el-form-item>
      <el-form-item label="代理服务器">
        <el-input v-model="form.proxy" placeholder="socks5://127.0.0.1:7897">
          <template #prefix>
            <el-icon class="text-slate-500"><Connection /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item label="无头模式">
        <div class="flex items-center justify-between w-full">
          <el-switch
            v-model="form.headless"
            active-text="On"
            inactive-text="Off"
            inline-prompt
          />
          <span class="text-[10px] text-slate-500">在后台运行浏览器</span>
        </div>
      </el-form-item>

      <div class="relative py-2 mt-4">
        <el-divider content-position="left">
          <span class="flex items-center gap-2 text-amber-400 font-medium text-xs uppercase tracking-wider">
            <el-icon><Connection /></el-icon>
            newAPI 同步
          </span>
        </el-divider>
      </div>
      <el-form-item label="newAPI 地址">
        <el-input v-model="form.newapi_base_url" placeholder="https://your-newapi.com" />
      </el-form-item>
      <el-form-item label="鉴权 Token">
        <el-input v-model="form.newapi_token" type="password" show-password placeholder="Bearer Token（个人设置-安全设置-系统访问令牌）" />
      </el-form-item>
      <el-form-item label="用户 ID">
        <el-input v-model="form.newapi_user_id" placeholder="New-Api-User，需与登录用户一致" />
      </el-form-item>
      <el-form-item label="渠道类型">
        <el-input-number v-model="form.newapi_type_openai" :min="1" controls-position="right" class="w-full" />
      </el-form-item>
      <el-form-item label="模型列表">
        <el-input v-model="form.newapi_models" type="textarea" :rows="3" placeholder="gpt-5.3,gpt-5,..." />
      </el-form-item>
      <el-form-item label="渠道Base URL">
        <el-input v-model="form.newapi_channel_base_url" placeholder="可留空，默认空字符串" />
      </el-form-item>

      <div class="relative py-2 mt-4">
        <el-divider content-position="left">
          <span class="flex items-center gap-2 text-sky-400 font-medium text-xs uppercase tracking-wider">
            <el-icon><Cpu /></el-icon>
            AWS IP 轮换
          </span>
        </el-divider>
      </div>
      <div class="text-[10px] text-slate-500 mb-2 leading-tight">配置后每次注册自动走不同 AWS 区域 IP，免费层每月 100 万次请求</div>
      <el-form-item label="Access Key ID">
        <el-input v-model="form.aws_access_key_id" placeholder="AKIAIOSFODNN7EXAMPLE" />
      </el-form-item>
      <el-form-item label="Secret Key">
        <el-input v-model="form.aws_secret_access_key" type="password" show-password placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="flex justify-end gap-3 pt-4">
        <button
          @click="$emit('close')"
          class="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm font-medium"
        >
          取消
        </button>
        <button
          @click="handleSave"
          :disabled="saving"
          class="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 text-sm font-medium transition-all flex items-center gap-2"
        >
          <span v-if="saving" class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
          {{ saving ? '保存中...' : '保存更改' }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Message, Cpu, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { configApi } from '../api'

const emit = defineEmits<{ close: [] }>()
const visible = ref(true)
const saving = ref(false)
const lastPresetIndex = ref(0)

const defaultPresets = () => [
  { name: 'Tempmail.lol', email_type: 'tempmail_lol', domain: '', imap_host: '', imap_port: 993, imap_user: '', imap_pass: '', tempmail_base_url: 'https://api.tempmail.lol/v2' },
  { name: 'QQ Mail', email_type: 'imap', domain: '', imap_host: 'imap.qq.com', imap_port: 993, imap_user: '', imap_pass: '' },
  { name: 'Outlook', email_type: 'imap', domain: 'outlook.com', imap_host: 'outlook.office365.com', imap_port: 993, imap_user: '', imap_pass: '' },
]

const form = ref({
  domain: '',
  imap_host: '',
  imap_port: 993,
  imap_user: '',
  imap_pass: '',
  email_prefix: 'auto',
  proxy: '',
  headless: false,
  log_dir: 'logs',
  run_count: 0,
  run_interval: 60,
  log_enabled: false,
  newapi_base_url: '',
  newapi_token: '',
  newapi_user_id: '',
  newapi_type_openai: 57,
  newapi_models: 'gpt-5.3,gpt-5,gpt-5-codex,gpt-5-codex-mini,gpt-5.1,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini,gpt-5.2,gpt-5.2-codex,gpt-5.3-codex,gpt-5-openai-compact,gpt-5-codex-openai-compact,gpt-5-codex-mini-openai-compact,gpt-5.1-openai-compact,gpt-5.1-codex-openai-compact,gpt-5.1-codex-max-openai-compact,gpt-5.1-codex-mini-openai-compact,gpt-5.2-openai-compact,gpt-5.2-codex-openai-compact,gpt-5.3-codex-openai-compact',
  newapi_channel_base_url: '',
  aws_access_key_id: '',
  aws_secret_access_key: '',
  email_presets: defaultPresets(),
  active_email_preset: 0,
})

const currentPresetType = computed(() => {
  return (form.value.email_presets[form.value.active_email_preset]?.email_type || 'imap').toLowerCase()
})

function syncFieldsFromPreset(idx: number) {
  const p = form.value.email_presets[idx]
  if (!p) return
  form.value.domain = p.domain || ''
  form.value.imap_host = p.imap_host || ''
  form.value.imap_port = p.imap_port || 993
  form.value.imap_user = p.imap_user || ''
  form.value.imap_pass = p.imap_pass || ''
}

function syncFieldsToPreset(idx: number) {
  const p = form.value.email_presets[idx]
  if (!p) return
  p.domain = form.value.domain
  p.imap_host = form.value.imap_host
  p.imap_port = form.value.imap_port
  p.imap_user = form.value.imap_user
  p.imap_pass = form.value.imap_pass
}

function onPresetChange(idx: number) {
  syncFieldsToPreset(lastPresetIndex.value)
  syncFieldsFromPreset(idx)
  lastPresetIndex.value = idx
}

function onTempmailBaseUrlChange(val: string) {
  const p = form.value.email_presets[form.value.active_email_preset]
  if (!p) return
  p.tempmail_base_url = (val || '').trim() || 'https://api.tempmail.lol/v2'
}

onMounted(async () => {
  try {
    const { data } = await configApi.get()
    Object.assign(form.value, data)
    if (!form.value.proxy) form.value.proxy = ''
    if (!form.value.newapi_base_url) form.value.newapi_base_url = ''
    if (!form.value.newapi_token) form.value.newapi_token = ''
    if (!form.value.newapi_user_id) form.value.newapi_user_id = ''
    if (!form.value.newapi_type_openai) form.value.newapi_type_openai = 57
    if (!form.value.newapi_models) form.value.newapi_models = 'gpt-5.3,gpt-5,gpt-5-codex,gpt-5-codex-mini,gpt-5.1,gpt-5.1-codex,gpt-5.1-codex-max,gpt-5.1-codex-mini,gpt-5.2,gpt-5.2-codex,gpt-5.3-codex,gpt-5-openai-compact,gpt-5-codex-openai-compact,gpt-5-codex-mini-openai-compact,gpt-5.1-openai-compact,gpt-5.1-codex-openai-compact,gpt-5.1-codex-max-openai-compact,gpt-5.1-codex-mini-openai-compact,gpt-5.2-openai-compact,gpt-5.2-codex-openai-compact,gpt-5.3-codex-openai-compact'
    if (!form.value.newapi_channel_base_url) form.value.newapi_channel_base_url = ''
    if (!form.value.aws_access_key_id) form.value.aws_access_key_id = ''
    if (!form.value.aws_secret_access_key) form.value.aws_secret_access_key = ''
    if (!form.value.email_presets?.length) form.value.email_presets = defaultPresets()
    if (!form.value.email_presets.some((p: any) => (p.email_type || '').toLowerCase() === 'tempmail_lol')) {
      form.value.email_presets.unshift({
        name: 'Tempmail.lol',
        email_type: 'tempmail_lol',
        domain: '',
        imap_host: '',
        imap_port: 993,
        imap_user: '',
        imap_pass: '',
        tempmail_base_url: 'https://api.tempmail.lol/v2',
      } as any)
    }
    if (form.value.active_email_preset == null) form.value.active_email_preset = 0
    if (form.value.active_email_preset < 0 || form.value.active_email_preset >= form.value.email_presets.length) {
      form.value.active_email_preset = 0
    }
    lastPresetIndex.value = form.value.active_email_preset
    syncFieldsFromPreset(form.value.active_email_preset)
  } catch {}
})

async function handleSave() {
  saving.value = true
  try {
    syncFieldsToPreset(form.value.active_email_preset)
    const payload = { ...form.value }
    if (!payload.proxy) payload.proxy = null as any
    await configApi.update(payload)
    ElMessage.success('Configuration saved')
    emit('close')
  } catch {
    ElMessage.error('Failed to save configuration')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* Scoped styles for spacing tweaks if needed */
:deep(.config-dialog) {
  min-width: 700px;
  margin: 0 auto;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #94a3b8;
}
</style>
