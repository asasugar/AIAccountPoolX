<template>
  <div class="h-full flex flex-col bg-slate-900/50 backdrop-blur-sm relative z-20">
    <!-- Logo -->
    <div class="p-6 border-b border-slate-800/50 relative overflow-hidden">
      <!-- Glow effect -->
      <div class="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-indigo-500/10 to-purple-500/5 pointer-events-none"></div>

      <div class="flex items-center gap-4 relative z-10">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 ring-1 ring-white/20">
          <span class="text-xl">🤖</span>
        </div>
        <div>
          <h1 class="text-base font-bold text-white tracking-wide">AIAccountPool</h1>
          <p class="text-[10px] text-indigo-200/60 font-medium tracking-wider uppercase">多平台管理器</p>
        </div>
      </div>
    </div>

    <!-- 状态卡片 -->
    <div class="p-4">
      <div class="relative overflow-hidden rounded-2xl bg-slate-800/40 border border-slate-700/50 p-5 group hover:border-indigo-500/30 transition-colors duration-300">
        <!-- 背景装饰 -->
        <div class="absolute -right-6 -top-6 w-24 h-24 bg-indigo-500/10 rounded-full blur-2xl group-hover:bg-indigo-500/20 transition-all duration-500"></div>

        <div class="relative z-10">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-2.5">
              <span class="relative flex h-2.5 w-2.5">
                <span v-if="currentEngine?.running" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="currentEngine?.running ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-600'"></span>
              </span>
              <span class="text-sm font-semibold tracking-wide" :class="currentEngine?.running ? 'text-emerald-400' : 'text-slate-500'">
                {{ currentEngine?.running ? '运行中' : '已停止' }}
              </span>
            </div>
            <span v-if="currentEngine?.running" class="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">
              第 {{ currentEngine.current_round }}{{ currentEngine.total_rounds > 0 ? '/' + currentEngine.total_rounds : '' }} 轮
            </span>
          </div>

          <!-- 统计数字 -->
          <div class="grid grid-cols-3 gap-2">
            <div class="text-center p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <div class="text-xl font-bold text-emerald-400 tabular-nums">{{ store.stats.success_count }}</div>
              <div class="text-[10px] font-medium text-emerald-500/60 uppercase tracking-wider mt-1">成功</div>
            </div>
            <div class="text-center p-2 rounded-lg bg-rose-500/5 border border-rose-500/10">
              <div class="text-xl font-bold text-rose-400 tabular-nums">{{ store.stats.fail_count }}</div>
              <div class="text-[10px] font-medium text-rose-500/60 uppercase tracking-wider mt-1">失败</div>
            </div>
            <div class="text-center p-2 rounded-lg bg-sky-500/5 border border-sky-500/10">
              <div class="text-xl font-bold text-sky-400 tabular-nums">{{ store.stats.total_count }}</div>
              <div class="text-[10px] font-medium text-sky-500/60 uppercase tracking-wider mt-1">总数</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 控制面板 -->
    <div class="px-4 pb-4">
      <div class="rounded-2xl bg-slate-800/40 border border-slate-700/50 p-4">
        <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <el-icon><Operation /></el-icon>
          任务控制
        </div>

        <div class="grid grid-cols-2 gap-3 mb-3">
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">Count (0=Inf)</label>
            <el-input-number
              v-model="taskCount"
              :min="0"
              size="small"
              controls-position="right"
              class="!w-full custom-input-number"
            />
          </div>
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">
              {{ taskMode === 'parallel' ? '统一间隔(秒)' : '默认间隔(秒)' }}
            </label>
            <el-input-number
              v-model="taskInterval"
              :min="1"
              size="small"
              controls-position="right"
              class="!w-full custom-input-number"
            />
          </div>
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">并发</label>
            <el-input-number
              v-model="taskConcurrency"
              :min="1"
              size="small"
              controls-position="right"
              class="!w-full custom-input-number"
            />
          </div>
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">调度模式</label>
            <el-select v-model="taskMode" size="small" class="!w-full custom-select">
              <el-option label="并行" value="parallel" />
              <el-option label="流水线" value="pipeline" />
            </el-select>
          </div>
        </div>

        <div v-if="taskMode === 'pipeline'" class="grid grid-cols-2 gap-3 mb-4">
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">最小间隔</label>
            <el-input-number
              v-model="taskIntervalMin"
              :min="0"
              size="small"
              controls-position="right"
              class="!w-full custom-input-number"
            />
          </div>
          <div class="rounded-xl border border-slate-700/50 bg-slate-900/35 p-2.5">
            <label class="text-[10px] font-medium text-slate-400 mb-1.5 block">最大间隔</label>
            <el-input-number
              v-model="taskIntervalMax"
              :min="0"
              size="small"
              controls-position="right"
              class="!w-full custom-input-number"
            />
          </div>
        </div>

        <button
          v-if="!currentEngine?.running"
          class="w-full h-11 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 text-white text-sm font-semibold tracking-wide hover:shadow-lg hover:shadow-emerald-500/20 hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center gap-2"
          @click="handleStart"
        >
          <el-icon><VideoPlay /></el-icon>
          启动任务
        </button>
        <button
          v-else
          class="w-full h-11 rounded-xl bg-gradient-to-r from-rose-600 to-rose-500 text-white text-sm font-semibold tracking-wide hover:shadow-lg hover:shadow-rose-500/20 hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center gap-2"
          @click="handleStop"
        >
          <el-icon><VideoPause /></el-icon>
          停止任务
        </button>
      </div>
    </div>

    <!-- 平台列表 -->
    <div class="flex-1 overflow-y-auto px-4 custom-scrollbar">
      <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2 sticky top-0 bg-slate-900/95 py-2 backdrop-blur z-10">
        <el-icon><Grid /></el-icon>
        平台列表
      </div>

      <div class="space-y-1.5 pb-4">
        <button
          v-for="p in store.platforms"
          :key="p.id"
          class="w-full group flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 border text-left relative overflow-hidden"
          :class="store.currentPlatform === p.id
            ? 'bg-indigo-600/10 border-indigo-500/30 shadow-[0_0_15px_rgba(79,70,229,0.15)]'
            : 'bg-transparent border-transparent hover:bg-slate-800/50 hover:border-slate-700/50'"
          @click="store.currentPlatform = p.id; store.fetchStats()"
        >
          <!-- Active highlight bar -->
          <div v-if="store.currentPlatform === p.id" class="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-indigo-500 rounded-r-full shadow-[0_0_8px_rgba(99,102,241,0.8)]"></div>

          <div class="flex items-center gap-3 pl-2">
            <span class="text-xl filter drop-shadow-lg">{{ p.icon }}</span>
            <span class="text-sm font-medium transition-colors" :class="store.currentPlatform === p.id ? 'text-indigo-100' : 'text-slate-400 group-hover:text-slate-200'">{{ p.name }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span v-if="p.running" class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span class="text-xs font-mono px-2 py-0.5 rounded-md transition-colors"
                  :class="store.currentPlatform === p.id ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-800 text-slate-500 group-hover:bg-slate-700 group-hover:text-slate-400'">
              {{ p.total_count }}
            </span>
          </div>
        </button>
      </div>
    </div>

    <!-- 底部工具栏 -->
    <div class="p-4 border-t border-slate-800/50 bg-slate-900/40">
      <div class="flex gap-2">
        <button
          @click="store.toggleTheme()"
          class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all text-sm font-medium group"
        >
          <el-icon><MoonNight v-if="store.theme === 'dark'" /><Sunny v-else /></el-icon>
          {{ store.theme === 'dark' ? '浅色主题' : '深色主题' }}
        </button>
        <button
          @click="showConfig = true"
          class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all text-sm font-medium group"
        >
          <el-icon class="group-hover:rotate-90 transition-transform duration-500"><Setting /></el-icon>
          系统配置
        </button>
      </div>
    </div>

    <ConfigDialog v-if="showConfig" @close="showConfig = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { VideoPlay, VideoPause, Setting, Operation, Grid, MoonNight, Sunny } from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'
import ConfigDialog from './ConfigDialog.vue'

const store = useAppStore()
const taskCount = ref(0)
const taskInterval = ref(60)
const taskConcurrency = ref(1)
const taskMode = ref<'parallel' | 'pipeline'>('parallel')
const taskIntervalMin = ref(0)
const taskIntervalMax = ref(0)
const showConfig = ref(false)

const currentEngine = computed(() =>
  store.platforms.find(p => p.id === store.currentPlatform)
)

let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => store.fetchStats(), 3000)
}

function stopPolling() {
  if (!pollTimer) return
  clearInterval(pollTimer)
  pollTimer = null
}

onMounted(() => {
  store.fetchPlatforms()
  store.fetchStats()
})

watch(
  () => currentEngine.value?.running,
  (running) => {
    if (running) startPolling()
    else stopPolling()
  },
  { immediate: true }
)

onUnmounted(() => {
  stopPolling()
})

async function handleStart() {
  const minVal = Math.max(0, taskIntervalMin.value)
  const maxVal = Math.max(minVal, taskIntervalMax.value)
  await store.startTask(
    taskCount.value,
    taskInterval.value,
    taskConcurrency.value,
    taskMode.value,
    minVal,
    maxVal
  )
}

async function handleStop() {
  await store.stopTask()
}
</script>

<style scoped>
/* Custom Scrollbar for Sidebar */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
}

/* Override Element Plus Input Number */
.custom-input-number .el-input__wrapper {
  background-color: rgba(30, 41, 59, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(51, 65, 85, 0.5) !important;
  transition: all 0.2s;
  border-radius: 8px;
}
.custom-input-number .el-input__wrapper:hover,
.custom-input-number .el-input__wrapper.is-focus {
  border-color: rgba(99, 102, 241, 0.5) !important;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.2) !important;
}
.custom-input-number .el-input__inner {
  color: #e2e8f0 !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.custom-input-number .el-input-number__decrease,
.custom-input-number .el-input-number__increase {
  background-color: transparent !important;
  border-left: 1px solid rgba(51, 65, 85, 0.3) !important;
  color: #94a3b8 !important;
}
.custom-input-number .el-input-number__decrease:hover,
.custom-input-number .el-input-number__increase:hover {
  color: #6366f1 !important;
  background-color: rgba(99, 102, 241, 0.1) !important;
}

.custom-select .el-select__wrapper {
  min-height: 32px !important;
  background-color: rgba(30, 41, 59, 0.5) !important;
  box-shadow: none !important;
  border: 1px solid rgba(51, 65, 85, 0.5) !important;
  border-radius: 8px !important;
}
.custom-select .el-select__wrapper:hover,
.custom-select .el-select__wrapper.is-focused {
  border-color: rgba(99, 102, 241, 0.5) !important;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.2) !important;
}
.custom-select .el-select__selected-item {
  color: #e2e8f0 !important;
  font-size: 12px !important;
}
</style>
