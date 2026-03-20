<template>
  <div class="h-full flex flex-col bg-slate-950/50 backdrop-blur-sm relative z-10">
    <!-- 顶栏 -->
    <div class="flex items-center justify-between px-5 py-3 border-b border-slate-800/50 bg-slate-900/40 backdrop-blur-md sticky top-0 z-20">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <div class="relative flex h-2 w-2">
             <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
             <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></span>
          </div>
          <span class="text-sm font-semibold text-slate-200 tracking-wide">实时日志</span>
        </div>
        <span class="text-[10px] font-mono text-slate-500 bg-slate-800/50 px-2 py-0.5 rounded-full border border-slate-700/50">
          {{ visibleLogs.length }}/{{ logs.length }} events
        </span>
      </div>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2 cursor-pointer group select-none">
          <input type="checkbox" v-model="store.liveLog" class="sr-only peer" />
          <div class="relative w-8 h-4.5 bg-slate-700/50 rounded-full peer peer-checked:bg-indigo-500/30 transition-all duration-300 border border-slate-600 peer-checked:border-indigo-500/50">
            <div class="absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-slate-400 rounded-full transition-all duration-300 peer-checked:translate-x-3.5 peer-checked:bg-indigo-400 shadow-sm"></div>
          </div>
          <span class="text-xs font-medium text-slate-500 group-hover:text-slate-300 transition-colors">自动滚动</span>
        </label>
        <button
          @click="store.clearLogs()"
          class="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-rose-400 transition-colors px-2.5 py-1.5 rounded-lg hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20"
        >
          <el-icon><Delete /></el-icon>
          清空日志
        </button>
      </div>
    </div>

    <!-- 日志内容 -->
    <div ref="logContainer" class="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed custom-scrollbar scroll-smooth">
      <div class="space-y-0.5">
        <div
          v-if="hiddenLogCount > 0"
          class="sticky top-0 z-10 py-2 px-3 mb-2 rounded-lg bg-amber-500/10 text-amber-200 border border-amber-500/20 text-[11px]"
        >
          已折叠更早的 {{ hiddenLogCount }} 条日志，仅显示最近 {{ visibleLogs.length }} 条
        </div>
        <div
          v-for="entry in visibleLogs"
          :key="entry.id"
          class="flex gap-3 py-1.5 px-3 rounded-lg hover:bg-white/[0.03] transition-colors group border border-transparent hover:border-white/[0.05]"
        >
          <span class="text-slate-600 shrink-0 select-none tabular-nums font-medium text-[10px] pt-0.5 opacity-70 group-hover:opacity-100 transition-opacity">{{ formatTime(entry.timestamp) }}</span>
          <div class="flex-1 flex gap-3 min-w-0">
             <span
              class="shrink-0 px-1.5 py-0.5 rounded-[4px] text-[10px] font-bold uppercase tracking-wider h-fit border border-current border-opacity-20"
              :class="tagClass(entry.level)"
            >
              {{ levelLabel(entry.level) }}
            </span>
            <span class="break-all whitespace-pre-wrap" :class="messageColor(entry.level)">
              {{ entry.message }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="logs.length === 0" class="flex flex-col items-center justify-center h-full text-center opacity-40 select-none">
        <div class="w-20 h-20 rounded-3xl bg-slate-800/50 flex items-center justify-center mb-4 ring-1 ring-white/5">
          <el-icon :size="32" class="text-slate-600"><Document /></el-icon>
        </div>
        <p class="text-slate-500 text-sm font-medium">暂无日志</p>
        <p class="text-slate-600 text-xs mt-1">等待任务启动...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick } from 'vue'
import { Delete, Document } from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const logs = computed(() => store.logs)
const MAX_VISIBLE_LOGS = 500
const visibleLogs = computed(() => {
  const allLogs = logs.value
  if (allLogs.length <= MAX_VISIBLE_LOGS) return allLogs
  return allLogs.slice(-MAX_VISIBLE_LOGS)
})
const hiddenLogCount = computed(() => Math.max(0, logs.value.length - visibleLogs.value.length))
const logContainer = ref<HTMLElement | null>(null)

watch(
  () => store.logs.length,
  async () => {
    if (store.liveLog && logContainer.value) {
      await nextTick()
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }
)

function formatTime(ts: string): string {
  return ts.split(' ')[1] || ts
}

function tagClass(level: string): string {
  const map: Record<string, string> = {
    info: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    step: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  }
  return map[level] || 'bg-slate-500/10 text-slate-400 border-slate-500/20'
}

function levelLabel(level: string): string {
  const map: Record<string, string> = {
    info: 'INFO', success: 'OK', warning: 'WARN', error: 'ERR', step: 'STEP',
  }
  return map[level] || level.toUpperCase()
}

function messageColor(level: string): string {
  const map: Record<string, string> = {
    error: 'text-rose-300 font-medium',
    warning: 'text-amber-200',
    success: 'text-emerald-300',
    step: 'text-violet-300',
    info: 'text-slate-300'
  }
  return map[level] || 'text-slate-400'
}
</script>
