<template>
  <div class="h-full flex flex-col bg-slate-950/30 relative z-10">
    <!-- Header -->
    <div class="p-4 border-b border-slate-800/50 bg-slate-900/20 backdrop-blur-md sticky top-0 z-20">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 ring-1 ring-white/10">
            <el-icon class="text-white text-lg"><User /></el-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-white">账号管理</h2>
            <p class="text-[10px] text-slate-500">共 {{ stats.total }} 个账号 · {{ stats.active }} 活跃</p>
          </div>
        </div>
        <button
          @click="showAddDialog = true"
          class="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all"
        >
          <el-icon><Plus /></el-icon>
          添加
        </button>
      </div>

      <!-- 筛选栏 -->
      <div class="flex gap-2">
        <el-select v-model="filterPlatform" size="small" class="w-28" placeholder="平台" clearable @change="fetchAccounts">
          <el-option label="全部" value="" />
          <el-option label="OpenAI" value="openai" />
          <el-option label="Claude" value="claude" />
        </el-select>
        <el-select v-model="filterStatus" size="small" class="w-24" placeholder="状态" clearable @change="fetchAccounts">
          <el-option label="全部" value="" />
          <el-option label="活跃" value="active" />
          <el-option label="封禁" value="banned" />
        </el-select>
        <el-input v-model="searchQuery" size="small" placeholder="搜索邮箱..." clearable @input="debouncedSearch" class="flex-1">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <!-- 账号表格 -->
    <div class="flex-1 overflow-auto p-4">
      <el-table
        :data="accounts"
        style="width: 100%"
        size="small"
        :header-cell-style="{ background: 'rgba(30,41,59,0.5)', color: '#94a3b8', fontWeight: 600, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', border: 'none' }"
        :row-style="{ background: 'transparent' }"
        :cell-style="{ border: 'none', padding: '12px 8px' }"
        row-class-name="hover:bg-slate-800/30 transition-colors"
        empty-text="暂无账号数据"
      >
        <el-table-column label="平台" width="90">
          <template #default="{ row }">
            <span class="px-2 py-1 rounded text-[10px] font-bold uppercase"
                  :class="row.platform === 'openai' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-violet-500/10 text-violet-400'">
              {{ row.platform }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-slate-200 font-medium">{{ row.email }}</span>
          </template>
        </el-table-column>
        <el-table-column label="密码" width="120">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <span class="text-slate-400 font-mono text-xs">{{ row.password ? '••••••' : '-' }}</span>
              <el-tooltip v-if="row.password" content="复制密码" placement="top">
                <button @click="copyPassword(row)" class="text-indigo-400 hover:text-indigo-300 transition-colors">
                  <el-icon :size="14"><CopyDocument /></el-icon>
                </button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-slate-400 text-xs">{{ row.username || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="姓名" width="100">
          <template #default="{ row }">
            <span class="text-slate-400 text-xs">{{ row.first_name ? `${row.first_name} ${row.last_name || ''}` : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="生日" width="100">
          <template #default="{ row }">
            <span class="text-slate-500 text-xs">{{ row.birth_year ? `${row.birth_year}/${row.birth_month}/${row.birth_day}` : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium" :class="getStatusClass(row.status)">
              <span class="w-1.5 h-1.5 rounded-full" :class="getStatusDotClass(row.status)"></span>
              {{ getStatusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-0.5">
              <el-tooltip content="查看 Token" placement="top">
                <button @click="viewToken(row)" class="w-7 h-7 rounded hover:bg-indigo-500/20 flex items-center justify-center text-indigo-400 hover:text-indigo-300 transition-colors">
                  <el-icon :size="14"><Key /></el-icon>
                </button>
              </el-tooltip>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <button class="w-7 h-7 rounded hover:bg-rose-500/20 flex items-center justify-center text-rose-400 hover:text-rose-300 transition-colors">
                    <el-icon :size="14"><Delete /></el-icon>
                  </button>
                </template>
              </el-popconfirm>
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
        @current-change="fetchAccounts"
        @size-change="fetchAccounts"
      />
    </div>

    <!-- Token 详情弹窗 -->
    <el-dialog
      v-model="showTokenDialog"
      title="Token 详情"
      width="600px"
      class="custom-dialog"
      :close-on-click-modal="false"
      align-center
    >
      <div v-if="currentToken" class="space-y-4">
        <div class="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
          <span class="text-slate-400 text-sm font-medium">状态</span>
          <span
            class="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider border"
            :class="currentToken.status === 'active'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'"
          >
            {{ currentToken.status === 'active' ? '活跃' : '无效' }}
          </span>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
            <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">使用次数</div>
            <div class="text-white text-lg font-mono font-medium">{{ currentToken.used_count }}</div>
          </div>
          <div class="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
            <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">最后使用</div>
            <div class="text-white text-sm font-medium">{{ formatTime(currentToken.last_used) }}</div>
          </div>
        </div>
        <div class="space-y-2">
          <div class="text-slate-400 text-xs font-bold uppercase tracking-wider">Access Token</div>
          <div class="p-4 bg-slate-950 rounded-xl font-mono text-xs text-slate-300 break-all max-h-32 overflow-y-auto border border-slate-800 custom-scrollbar select-all">
            {{ currentToken.access_token }}
          </div>
        </div>
        <div class="space-y-2">
          <div class="text-slate-400 text-xs font-bold uppercase tracking-wider">Refresh Token</div>
          <div class="p-4 bg-slate-950 rounded-xl font-mono text-xs text-slate-300 break-all max-h-32 overflow-y-auto border border-slate-800 custom-scrollbar select-all">
            {{ currentToken.refresh_token || '无' }}
          </div>
        </div>
      </div>
      <div v-else class="text-center py-12 text-slate-500">
        <el-icon size="40" class="mb-2 opacity-50"><Key /></el-icon>
        <p>该账号暂无 Token</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 pt-4 border-t border-slate-700/50">
          <button
            @click="showTokenDialog = false"
            class="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm font-medium"
          >
            关闭
          </button>
          <button
            v-if="currentToken"
            @click="copyToken"
            class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 text-sm font-medium transition-all"
          >
            复制 Access Token
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 添加账号弹窗 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加账号"
      width="500px"
      class="custom-dialog"
      :close-on-click-modal="false"
      align-center
    >
      <el-form :model="newAccount" label-position="top" class="custom-form">
        <el-form-item label="平台">
          <el-select v-model="newAccount.platform" class="w-full custom-select-large">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Claude" value="claude" />
          </el-select>
        </el-form-item>

        <el-form-item label="邮箱" required>
          <el-input v-model="newAccount.email" placeholder="name@example.com" class="custom-input" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input v-model="newAccount.password" placeholder="Account password" show-password class="custom-input" />
        </el-form-item>

        <el-form-item label="用户名">
          <el-input v-model="newAccount.username" placeholder="Username (optional)" class="custom-input" />
        </el-form-item>

        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="名">
            <el-input v-model="newAccount.first_name" placeholder="First Name" class="custom-input" />
          </el-form-item>
          <el-form-item label="姓">
            <el-input v-model="newAccount.last_name" placeholder="Last Name" class="custom-input" />
          </el-form-item>
        </div>

        <el-form-item label="生日">
          <div class="flex gap-2 w-full">
            <el-input-number v-model="newAccount.birth_year" :min="1950" :max="2010" placeholder="YYYY" controls-position="right" class="flex-1 custom-input-number" />
            <el-input-number v-model="newAccount.birth_month" :min="1" :max="12" placeholder="MM" controls-position="right" class="w-24 custom-input-number" />
            <el-input-number v-model="newAccount.birth_day" :min="1" :max="31" placeholder="DD" controls-position="right" class="w-24 custom-input-number" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-3 pt-4 border-t border-slate-700/50">
          <button
            @click="showAddDialog = false"
            class="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm font-medium"
          >
            取消
          </button>
          <button
            @click="handleAdd"
            :disabled="adding"
            class="px-6 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 text-sm font-medium transition-all flex items-center gap-2"
          >
            <span v-if="adding" class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
            {{ adding ? '添加中...' : '添加账号' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { User, Plus, Search, Key, CopyDocument, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { accountApi } from '../api'

interface Account {
  id: number
  platform: string
  email: string
  password?: string
  username?: string
  first_name?: string
  last_name?: string
  birth_year?: number
  birth_month?: number
  birth_day?: number
  status: string
  verified: boolean
  register_ip?: string
  created_at: string
}

interface TokenInfo {
  id: string
  platform: string
  email: string
  access_token: string
  refresh_token?: string
  status: string
  used_count: number
  last_used?: string
}

const accounts = ref<Account[]>([])
const searchQuery = ref('')
const filterPlatform = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const totalCount = ref(0)
const pageSize = ref(20)

const stats = reactive({ total: 0, active: 0, verified: 0, banned: 0 })

const showTokenDialog = ref(false)
const currentToken = ref<TokenInfo | null>(null)

const showAddDialog = ref(false)
const adding = ref(false)
const newAccount = reactive({
  platform: 'openai',
  email: '',
  password: '',
  username: '',
  first_name: '',
  last_name: '',
  birth_year: 1990,
  birth_month: 1,
  birth_day: 1,
})

let pollTimer: ReturnType<typeof setInterval>
let debounceTimer: ReturnType<typeof setTimeout>

onMounted(() => {
  fetchAccounts()
  fetchStats()
  pollTimer = setInterval(fetchStats, 30000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
})

async function fetchAccounts() {
  try {
    const { data } = await accountApi.list({
      platform: filterPlatform.value,
      search: searchQuery.value,
      status: filterStatus.value,
      page: currentPage.value,
      page_size: pageSize.value,
      include_password: true,
    })
    accounts.value = data.items
    totalCount.value = data.total
  } catch {}
}

async function fetchStats() {
  try {
    const { data } = await accountApi.stats(filterPlatform.value)
    Object.assign(stats, data)
  } catch {}
}

function debouncedSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchAccounts()
  }, 300)
}

async function handleDelete(id: number) {
  try {
    await accountApi.delete(id)
    ElMessage.success('Deleted successfully')
    fetchAccounts()
    fetchStats()
  } catch {}
}

async function viewToken(account: Account) {
  try {
    const { data } = await accountApi.getToken(account.id)
    currentToken.value = data.has_token ? data.token : null
    showTokenDialog.value = true
  } catch {}
}

function copyPassword(account: Account) {
  if (account.password) {
    navigator.clipboard.writeText(account.password).then(() => {
      ElMessage.success('Password copied')
    })
  } else {
    ElMessage.warning('No password saved for this account')
  }
}

function copyToken() {
  if (currentToken.value?.access_token) {
    navigator.clipboard.writeText(currentToken.value.access_token).then(() => {
      ElMessage.success('Token copied')
    })
  }
}

async function handleAdd() {
  if (!newAccount.email) {
    ElMessage.warning('Email is required')
    return
  }

  adding.value = true
  try {
    await accountApi.create(newAccount)
    ElMessage.success('Account added successfully')
    showAddDialog.value = false
    // Reset form
    Object.assign(newAccount, {
      platform: 'openai', email: '', password: '', username: '',
      first_name: '', last_name: '', birth_year: 1990, birth_month: 1, birth_day: 1,
    })
    fetchAccounts()
    fetchStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || 'Failed to add account')
  } finally {
    adding.value = false
  }
}

function getStatusClass(status: string): string {
  if (status === 'active') return 'bg-emerald-500/10 text-emerald-400'
  if (status === 'banned') return 'bg-rose-500/10 text-rose-400'
  return 'bg-slate-500/10 text-slate-400'
}

function getStatusDotClass(status: string): string {
  if (status === 'active') return 'bg-emerald-400'
  if (status === 'banned') return 'bg-rose-400'
  return 'bg-slate-500'
}

function getStatusText(status: string): string {
  if (status === 'active') return 'Active'
  if (status === 'banned') return 'Banned'
  return 'Unverified'
}

function formatTime(time?: string): string {
  if (!time) return 'Never'
  try {
    const d = new Date(time)
    return d.toLocaleString()
  } catch {
    return time
  }
}
</script>

<style scoped>
/* Scoped styles won't work easily for Element Plus internals unless using :deep,
   but for Dialogs appended to body we need global override or custom-class strategy.
   Here we rely on custom classes and some global CSS assumed in style.css or strict selectors. */

.custom-select .el-input__wrapper {
  background-color: rgba(30, 41, 59, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(51, 65, 85, 0.5) !important;
  border-radius: 8px;
}
.custom-select .el-input__inner {
  color: #e2e8f0 !important;
}

/* Dialog Styles Override */
.custom-dialog {
  background-color: #0f172a !important; /* slate-900 */
  border: 1px solid rgba(51, 65, 85, 0.5) !important;
  border-radius: 16px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
}
.custom-dialog .el-dialog__title {
  color: #f1f5f9 !important; /* slate-100 */
}
.custom-dialog .el-dialog__headerbtn .el-dialog__close {
  color: #94a3b8 !important;
}
.custom-dialog .el-dialog__body {
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* Form Styles */
.custom-form .el-form-item__label {
  color: #94a3b8 !important; /* slate-400 */
  font-size: 12px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}
.custom-input .el-input__wrapper {
  background-color: rgba(15, 23, 42, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(51, 65, 85, 0.5) !important;
  border-radius: 8px;
  padding: 8px 12px !important;
}
.custom-input .el-input__wrapper.is-focus {
  border-color: rgba(99, 102, 241, 0.5) !important;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.2) !important;
}
.custom-input .el-input__inner {
  color: #f1f5f9 !important;
}

/* Pagination Override */
.custom-pagination .btn-prev,
.custom-pagination .btn-next,
.custom-pagination .el-pager li {
  background-color: rgba(30, 41, 59, 0.5) !important;
  color: #94a3b8 !important;
  border: 1px solid rgba(51, 65, 85, 0.3) !important;
  border-radius: 6px !important;
}
.custom-pagination .el-pager li.is-active {
  background-color: rgba(79, 70, 229, 0.2) !important;
  color: #818cf8 !important;
  border-color: rgba(79, 70, 229, 0.5) !important;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 3px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
}
</style>
