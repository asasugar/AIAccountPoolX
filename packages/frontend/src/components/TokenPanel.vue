<template>
  <div class="h-full flex flex-col bg-slate-950/30 relative z-10">
    <!-- Header -->
    <div class="p-4 border-b border-slate-800/50 bg-slate-900/20 backdrop-blur-md sticky top-0 z-20">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/20 ring-1 ring-white/10">
            <el-icon class="text-white text-lg"><Key /></el-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-white">账号管理</h2>
            <p class="text-[10px] text-slate-500">共 {{ tokenStats.total }} 个 · {{ tokenStats.active }} 活跃</p>
          </div>
        </div>
        <div class="flex items-center gap-1.5">
          <a
            href="https://github.com/asasugar/AIAccountPoolX"
            target="_blank"
            rel="noopener noreferrer"
            class="w-8 h-8 rounded-lg hover:bg-slate-800 flex items-center justify-center transition-colors border border-transparent hover:border-slate-700/50 text-slate-500 hover:text-slate-300"
          >
            <svg viewBox="0 0 24 24" class="w-4 h-4 fill-current" aria-hidden="true">
              <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.9.58.1.79-.25.79-.56 0-.28-.01-1.2-.02-2.18-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.17 1.75 1.17 1.02 1.76 2.68 1.25 3.34.95.1-.74.4-1.25.72-1.54-2.56-.29-5.26-1.28-5.26-5.71 0-1.26.45-2.28 1.17-3.09-.12-.29-.51-1.47.11-3.06 0 0 .96-.31 3.14 1.18a10.9 10.9 0 0 1 5.72 0c2.18-1.5 3.14-1.18 3.14-1.18.62 1.59.23 2.77.11 3.06.73.81 1.17 1.83 1.17 3.09 0 4.44-2.7 5.42-5.28 5.7.41.36.78 1.08.78 2.18 0 1.58-.01 2.85-.01 3.24 0 .31.21.67.8.56A11.52 11.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
            </svg>
          </a>
          <el-dropdown trigger="click">
            <button class="w-8 h-8 rounded-lg hover:bg-slate-800 flex items-center justify-center transition-colors border border-transparent hover:border-slate-700/50">
              <el-icon class="text-slate-500"><More /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleExport('')">导出全部</el-dropdown-item>
                <el-dropdown-item @click="handleExport(store.currentPlatform)">导出当前平台</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <div class="flex items-center justify-between gap-2 mb-3">
        <div class="flex items-center gap-2 text-[11px] text-slate-500">
          <span v-if="syncStatus.last_sync_at">上次同步: {{ formatSyncTime(syncStatus.last_sync_at) }}</span>
          <span v-if="syncStatus.status !== 'idle'" class="px-2 py-0.5 rounded" :class="syncStatus.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' : syncStatus.status === 'error' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'">
            {{ syncStatus.success_count }} 成功 / {{ syncStatus.fail_count }} 失败
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="handleRetryRefreshToken"
            :disabled="refreshingStatus3"
            class="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-violet-600/80 hover:bg-violet-500 text-white text-xs font-medium transition-all disabled:opacity-50"
          >
            <span v-if="refreshingStatus3" class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <el-icon v-else><RefreshRight /></el-icon>
            {{ refreshingStatus3 ? '刷新中...' : '一键刷新token' }}
          </button>
          <button
            @click="handleSyncNewApi"
            :disabled="syncing"
            class="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-600/80 hover:bg-amber-500 text-white text-xs font-medium transition-all disabled:opacity-50"
          >
            <span v-if="syncing" class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <el-icon v-else><Upload /></el-icon>
            {{ syncing ? '同步中...' : '一键同步 NewAPI' }}
          </button>
        </div>
      </div>
      <!-- 筛选栏 -->
      <div class="flex gap-2">
        <el-select v-model="filterPlatform" size="small" placeholder="平台" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option v-for="p in store.platforms" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="filterNewApiStatus" size="small" placeholder="NewAPI状态" clearable @change="handleFilterChange">
          <el-option label="已启用" value="1" />
          <el-option label="已禁用" value="2" />
          <el-option label="自动禁用" value="3" />
        </el-select>
        <el-select v-model="filterSyncedStatus" size="small" placeholder="同步状态" clearable @change="handleFilterChange">
          <el-option label="已同步" value="true" />
          <el-option label="待同步" value="false" />
        </el-select>
        <el-input v-model="searchQuery" size="small" placeholder="搜索邮箱..." clearable @input="debouncedSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <div v-if="selectedRows.length > 0" class="mt-3 flex items-center gap-3 rounded-lg bg-rose-500/10 border border-rose-500/20 px-3 py-2">
        <span class="text-sm text-rose-200">已选 {{ selectedRows.length }} 条</span>
        <el-button type="danger" size="small" :loading="batchDeleting" @click="handleBatchDelete">
          批量删除（同时删 newAPI 渠道）
        </el-button>
        <el-button size="small" text @click="clearSelection">取消选择</el-button>
      </div>
    </div>

    <!-- Token 表格 -->
    <div class="flex-1 overflow-auto p-4">
      <el-table
        ref="tableRef"
        :data="tokens"
        :row-key="(row: Token) => row.id"
        style="width: 100%"
        size="small"
        :header-cell-style="{ background: 'rgba(30,41,59,0.5)', color: '#94a3b8', fontWeight: 600, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', border: 'none' }"
        :row-style="{ background: 'transparent' }"
        :cell-style="{ border: 'none', padding: '12px 8px' }"
        row-class-name="hover:bg-slate-800/30 transition-colors"
        empty-text="暂无 Token 数据"
        @selection-change="selectedRows = $event"
      >
        <el-table-column type="selection" width="42" />
        <el-table-column label="平台" width="90">
          <template #default="{ row }">
            <span class="px-2 py-1 rounded text-[10px] font-bold uppercase"
                  :class="row.platform === 'openai' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-violet-500/10 text-violet-400'">
              {{ row.platform || 'openai' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <div>
              <div class="text-slate-200 font-medium text-xs">{{ row.email }}</div>
              <div v-if="row.first_name" class="text-slate-500 text-[10px] mt-0.5">{{ row.first_name }}{{ row.last_name ? ' ' + row.last_name : '' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="同步状态" width="110" align="center">
          <template #default="{ row }">
            <div class="flex flex-col items-center gap-1">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
                :class="row.synced_to_newapi ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'">
                <span class="w-1.5 h-1.5 rounded-full" :class="row.synced_to_newapi ? 'bg-emerald-400' : 'bg-slate-500'"></span>
                {{ row.synced_to_newapi ? '已同步' : 'Token刷新，待同步' }}
              </span>
              <span v-if="row.newApiChannelId != null" class="text-[10px] text-slate-500">渠道 #{{ row.newApiChannelId }}</span>
              <span
                v-if="row.newApiChannelId != null && row.newApiChannelStatus != null"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
                :class="getNewApiChannelStatusClass(row.newApiChannelStatus)"
              >
                <el-tooltip
                  v-if="row.newApiChannelOtherInfo != null && String(row.newApiChannelOtherInfo).trim() !== ''"
                  :content="getChannelOtherInfoText(row.newApiChannelOtherInfo)"
                  placement="top"
                  :show-after="200"
                >
                  <span>{{ getNewApiChannelStatusText(row.newApiChannelStatus) }}</span>
                </el-tooltip>
                <span v-else>{{ getNewApiChannelStatusText(row.newApiChannelStatus) }}</span>
              </span>
              <span v-if="row.account_status && row.account_status !== 'active'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium" :class="getAccountStatusClass(row.account_status)">
                {{ getAccountStatusText(row.account_status) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Access Token" min-width="160">
          <template #default="{ row }">
            <div class="flex items-center gap-1">
              <el-tooltip :content="row.access_token || '-'" placement="top" :show-after="300">
                <div class="font-mono text-[10px] text-slate-500 truncate flex-1">{{ row.access_token ? row.access_token.substring(0, 30) + '...' : '-' }}</div>
              </el-tooltip>
              <el-tooltip v-if="row.access_token" content="复制 Access Token" placement="top">
                <button @click="copyText(row.access_token)" class="shrink-0 w-5 h-5 rounded hover:bg-emerald-500/20 flex items-center justify-center text-emerald-500/60 hover:text-emerald-400 transition-colors">
                  <el-icon :size="12"><CopyDocument /></el-icon>
                </button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Refresh Token" min-width="160">
          <template #default="{ row }">
            <div class="flex items-center gap-1">
              <el-tooltip :content="row.refresh_token || '-'" placement="top" :show-after="300">
                <div class="font-mono text-[10px] text-slate-500 truncate flex-1">{{ row.refresh_token ? row.refresh_token.substring(0, 30) + '...' : '-' }}</div>
              </el-tooltip>
              <el-tooltip v-if="row.refresh_token" content="复制 Refresh Token" placement="top">
                <button @click="copyText(row.refresh_token)" class="shrink-0 w-5 h-5 rounded hover:bg-violet-500/20 flex items-center justify-center text-violet-500/60 hover:text-violet-400 transition-colors">
                  <el-icon :size="12"><CopyDocument /></el-icon>
                </button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-0.5 flex-wrap">
              <el-tooltip content="刷新 Token" placement="top">
                <button
                  @click="handleRefreshToken(row)"
                  :disabled="refreshLoadingId === row.id"
                  class="w-7 h-7 rounded hover:bg-violet-500/20 flex items-center justify-center text-violet-400/70 hover:text-violet-400 transition-colors disabled:opacity-50"
                >
                  <span v-if="refreshLoadingId === row.id" class="w-3.5 h-3.5 border-2 border-violet-400/30 border-t-violet-400 rounded-full animate-spin"></span>
                  <el-icon v-else :size="14"><RefreshRight /></el-icon>
                </button>
              </el-tooltip>
              <template v-if="row.newApiChannelId != null && row.synced_to_newapi === false">
                <el-tooltip content="更新渠道" placement="top">
                  <button
                    @click="handleUpdateChannel(row)"
                    :disabled="updateChannelLoadingId === row.newApiChannelId"
                    class="w-7 h-7 rounded hover:bg-amber-500/20 flex items-center justify-center text-amber-400/70 hover:text-amber-400 transition-colors disabled:opacity-50"
                  >
                    <span v-if="updateChannelLoadingId === row.newApiChannelId" class="w-3.5 h-3.5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin"></span>
                    <el-icon v-else :size="14"><Upload /></el-icon>
                  </button>
                </el-tooltip>
              </template>
              <template v-if="row.newApiChannelId != null">
                <el-tooltip content="测试渠道" placement="top">
                  <button
                    @click="handleTestChannel(row)"
                    :disabled="testChannelLoadingId === row.newApiChannelId"
                    class="w-7 h-7 rounded hover:bg-sky-500/20 flex items-center justify-center text-sky-400/70 hover:text-sky-400 transition-colors disabled:opacity-50"
                  >
                    <span v-if="testChannelLoadingId === row.newApiChannelId" class="w-3.5 h-3.5 border-2 border-sky-400/30 border-t-sky-400 rounded-full animate-spin"></span>
                    <el-icon v-else :size="14"><VideoPlay /></el-icon>
                  </button>
                </el-tooltip>
                <el-tooltip content="删除渠道" placement="top">
                  <el-popconfirm title="确定删除该 newAPI 渠道？" @confirm="handleDeleteChannel(row)">
                    <template #reference>
                      <button
                        :disabled="deleteChannelLoadingId === row.newApiChannelId"
                        class="w-7 h-7 rounded hover:bg-orange-500/20 flex items-center justify-center text-orange-400/70 hover:text-orange-400 transition-colors disabled:opacity-50"
                      >
                        <span v-if="deleteChannelLoadingId === row.newApiChannelId" class="w-3.5 h-3.5 border-2 border-orange-400/30 border-t-orange-400 rounded-full animate-spin"></span>
                        <el-icon v-else :size="14"><Remove /></el-icon>
                      </button>
                    </template>
                  </el-popconfirm>
                </el-tooltip>
              </template>
              <el-tooltip content="删除" placement="top">
                <el-popconfirm title="确定删除？删除后将同时删除 newAPI 对应渠道。" @confirm="handleDelete(row)">
                  <template #reference>
                    <button class="w-7 h-7 rounded hover:bg-rose-500/20 flex items-center justify-center text-rose-400 hover:text-rose-300 transition-colors">
                      <el-icon :size="14"><Delete /></el-icon>
                    </button>
                  </template>
                </el-popconfirm>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="p-3 border-t border-slate-800/50 flex items-center justify-between bg-slate-900/30">
      <span class="text-xs text-slate-500">共 {{ totalCount }} 条</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="totalCount"
        :page-sizes="[10, 20, 50, 100]"
        layout="sizes, prev, pager, next"
        small
        background
        @current-change="fetchTokens"
        @size-change="fetchTokens"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Search, CopyDocument, Delete, More, Key, Upload, RefreshRight, VideoPlay, Remove } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tokenApi, newapiApi } from '../api'
import { useAppStore } from '../stores/app'

interface Token {
  id: string
  email: string
  platform: string
  access_token: string
  refresh_token: string
  saved_at: string
  status: string
  used_count: number
  last_used: string | null
  in_use: boolean
  synced_to_newapi: boolean
  first_name: string | null
  last_name: string | null
  username: string | null
  account_status: string | null
  newApiChannelId?: number | null
  newApiChannelStatus?: number | string | null
  newApiChannelOtherInfo?: unknown
}

const store = useAppStore()
const tokens = ref<Token[]>([])
const searchQuery = ref('')
const filterPlatform = ref('')
const filterNewApiStatus = ref('')
const filterSyncedStatus = ref('')
const currentPage = ref(1)
const totalCount = ref(0)
const pageSize = ref(20)
const syncing = ref(false)
const refreshingStatus3 = ref(false)
const refreshLoadingId = ref<string | null>(null)
const testChannelLoadingId = ref<number | null>(null)
const deleteChannelLoadingId = ref<number | null>(null)
const updateChannelLoadingId = ref<number | null>(null)
const selectedRows = ref<Token[]>([])
const batchDeleting = ref(false)
const tableRef = ref<InstanceType<typeof import('element-plus').ElTable> | null>(null)
const syncStatus = ref<{ last_sync_at?: string; status: string; message: string; success_count: number; fail_count: number }>({
  status: 'idle',
  message: '',
  success_count: 0,
  fail_count: 0,
})

const tokenStats = computed(() => {
  const active = tokens.value.filter(t => t.status === 'active').length
  const total = totalCount.value
  const today = tokens.value.filter(t => {
    const d = new Date(t.saved_at)
    const now = new Date()
    return d.toDateString() === now.toDateString()
  }).length
  const s = store.stats
  const rate = s.total_count > 0 ? Math.round((s.success_count / s.total_count) * 100) : 0
  return { active, total, today, rate }
})

let pollTimer: ReturnType<typeof setInterval>
let debounceTimer: ReturnType<typeof setTimeout>

onMounted(() => {
  fetchTokens()
  fetchSyncStatus()
  pollTimer = setInterval(fetchTokens, 10000)
})

async function fetchSyncStatus() {
  try {
    const { data } = await newapiApi.syncStatus()
    syncStatus.value = data
  } catch {}
}

async function handleSyncNewApi() {
  syncing.value = true
  try {
    const { data } = await newapiApi.sync()
    syncStatus.value = data
    if (data.fail_count === 0) ElMessage.success(`已同步 ${data.success_count} 个渠道到 newAPI`)
    else if (data.success_count > 0) ElMessage.warning(`部分同步: ${data.success_count} 成功, ${data.fail_count} 失败`)
    else ElMessage.error(data.message || '同步失败')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '同步失败')
  } finally {
    syncing.value = false
  }
}

async function handleRetryRefreshToken() {
  refreshingStatus3.value = true
  try {
    const { data } = await tokenApi.list({
      platform: filterPlatform.value,
      page: 1,
      page_size: 10000,
      newApiChannelStatus: 3,
    })
    const allTokens: Token[] = data?.items || []
    const targetTokens = allTokens
    if (!targetTokens.length) {
      await ElMessageBox.alert('成功数量: 0\n失败账号:\n无', '再次刷新token结果', { type: 'info' })
      return
    }

    const results = await Promise.allSettled(
      targetTokens.map(t => tokenApi.refreshToken(t.id, t.platform || ''))
    )
    const failEmails: string[] = []
    let successCount = 0
    results.forEach((r, idx) => {
      if (r.status === 'fulfilled') successCount += 1
      else failEmails.push(targetTokens[idx]?.email || targetTokens[idx]?.id || '')
    })

    const failLines = failEmails.length ? failEmails.join('\n') : '无'
    await ElMessageBox.alert(`成功数量: ${successCount}\n失败账号:\n${failLines}`, '再次刷新token结果', { type: failEmails.length ? 'warning' : 'success' })
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '再次刷新token失败')
  } finally {
    refreshingStatus3.value = false
  }
}

function formatSyncTime(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes} 分钟前`
    if (hours < 24) return `${hours} 小时前`
    if (days < 7) return `${days} 天前`
    return d.toLocaleString()
  } catch {
    return iso
  }
}

onUnmounted(() => {
  clearInterval(pollTimer)
})

async function fetchTokens() {
  const selectedIds = new Set(selectedRows.value.map(r => r.id))
  try {
    const { data } = await tokenApi.list({
      platform: filterPlatform.value,
      search: searchQuery.value,
      page: currentPage.value,
      page_size: pageSize.value,
      newApiChannelStatus: filterNewApiStatus.value,
      syncedToNewapi: filterSyncedStatus.value,
    })
    tokens.value = data.items
    totalCount.value = data.total
    await nextTick()
    if (selectedIds.size && tableRef.value) {
      tokens.value.forEach((row: Token) => {
        tableRef.value?.toggleRowSelection(row, selectedIds.has(row.id))
      })
    }
  } catch {}
}

function handleFilterChange() {
  currentPage.value = 1
  fetchTokens()
}

function clearSelection() {
  selectedRows.value = []
  tableRef.value?.clearSelection()
}

function debouncedSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchTokens()
  }, 300)
}

async function handleRefreshToken(row: Token) {
  refreshLoadingId.value = row.id
  try {
    await tokenApi.refreshToken(row.id, row.platform || '')
    ElMessage.success('Token 已刷新')
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '刷新 Token 失败')
  } finally {
    refreshLoadingId.value = null
  }
}

async function handleTestChannel(row: Token) {
  const id = row.newApiChannelId
  if (id == null) return
  testChannelLoadingId.value = id
  try {
    const { data } = await newapiApi.testChannel(id)
    if (data?.ok) {
      const timeStr = data?.time != null ? `，耗时 ${Number(data.time).toFixed(2)}s` : ''
      ElMessage.success(`测试通过${timeStr}`)
    } else {
      ElMessage.warning('账号已不可用')
    }
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '测试失败')
  } finally {
    testChannelLoadingId.value = null
  }
}

async function handleUpdateChannel(row: Token) {
  const channelId = row.newApiChannelId
  if (channelId == null) return
  updateChannelLoadingId.value = channelId
  try {
    await newapiApi.updateChannel(channelId, row.id, row.platform || '')
    ElMessage.success('渠道已更新')
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '更新渠道失败')
  } finally {
    updateChannelLoadingId.value = null
  }
}

async function handleDeleteChannel(row: Token) {
  const id = row.newApiChannelId
  if (id == null) return
  deleteChannelLoadingId.value = id
  try {
    await newapiApi.deleteChannel(id)
    ElMessage.success('渠道已删除')
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除渠道失败')
  } finally {
    deleteChannelLoadingId.value = null
  }
}

async function handleBatchDelete() {
  const rows = selectedRows.value
  if (!rows.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${rows.length} 条？将同时删除 newAPI 对应渠道。`,
      '批量删除',
      { type: 'warning' }
    )
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const ids = rows.map(r => r.id)
    const { data } = await tokenApi.batchDelete(ids, filterPlatform.value || '')
    ElMessage.success(`已删除 ${data?.deleted_tokens ?? 0} 条 Token，${data?.deleted_channels ?? 0} 个渠道`)
    selectedRows.value = []
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

async function handleDelete(row: Token) {
  try {
    if (row.newApiChannelId != null) {
      try {
        await newapiApi.deleteChannel(row.newApiChannelId)
      } catch (e: any) {
        ElMessage.error(e?.response?.data?.detail || '删除 newAPI 渠道失败')
        return
      }
    }
    await tokenApi.delete(row.id, row.platform || '')
    ElMessage.success('已删除')
    fetchTokens()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制')
  }).catch(() => {})
}

async function handleExport(platform: string) {
  try {
    const { data } = await tokenApi.export(platform)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `tokens_export_${platform || 'all'}_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Export successful')
  } catch {}
}

function getAccountStatusClass(status: string): string {
  if (status === 'banned') return 'bg-rose-500/10 text-rose-400'
  if (status === 'unverified') return 'bg-yellow-500/10 text-yellow-400'
  if (status === 'active') return 'bg-sky-500/10 text-sky-400'
  return 'bg-slate-500/10 text-slate-400'
}

function getAccountStatusText(status: string): string {
  if (status === 'banned') return '已封禁'
  if (status === 'unverified') return '未验证'
  if (status === 'active') return '正常'
  return status
}

function getNewApiChannelStatusText(status: number | string | null | undefined): string {
  if (String(status) === '1') return '已启用'
  if (String(status) === '2') return '已禁用'
  if (String(status) === '3') return '自动禁用'
  return `状态 ${status ?? '-'}`
}

function getNewApiChannelStatusClass(status: number | string | null | undefined): string {
  if (String(status) === '1') return 'bg-emerald-500/10 text-emerald-400'
  if (String(status) === '2') return 'bg-rose-500/10 text-rose-400'
  if (String(status) === '3') return 'bg-amber-500/10 text-amber-400'
  return 'bg-slate-500/10 text-slate-400'
}

function getChannelOtherInfoText(otherInfo: unknown): string {
  if (typeof otherInfo === 'string') return otherInfo
  try {
    return JSON.stringify(otherInfo)
  } catch {
    return String(otherInfo ?? '')
  }
}
</script>
