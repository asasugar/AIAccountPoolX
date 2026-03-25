import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { statsApi, taskApi, platformApi } from '../api'

export interface LogEntry {
  id?: string
  timestamp: string
  level: string
  message: string
}

type StoredLogEntry = LogEntry & { id: string }

export interface PlatformInfo {
  id: string
  name: string
  icon: string
  running: boolean
  success_count: number
  fail_count: number
  total_count: number
  current_round: number
  total_rounds: number
  concurrency?: number
  active_workers?: number
}

export interface Stats {
  success_count: number
  fail_count: number
  total_count: number
  token_count: number
  active_token_count: number
  running: boolean
  platforms: PlatformInfo[]
}

const MAX_LOGS = 2000
const LOG_FLUSH_INTERVAL_MS = 80
const LOG_IMMEDIATE_FLUSH_SIZE = 100
let logSequence = 0

export const useAppStore = defineStore('app', () => {
  const logs = shallowRef<StoredLogEntry[]>([])
  const currentPlatform = ref('openai')
  const platforms = ref<PlatformInfo[]>([])
  const stats = ref<Stats>({
    success_count: 0,
    fail_count: 0,
    total_count: 0,
    token_count: 0,
    active_token_count: 0,
    running: false,
    platforms: [],
  })
  const liveLog = ref(true)
  const theme = ref<'dark' | 'light'>('dark')
  let pendingLogs: StoredLogEntry[] = []
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  const seenLogIds = new Set<string>()
  const pendingLogIds = new Set<string>()

  function flushLogs() {
    if (flushTimer) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
    if (pendingLogs.length === 0) return

    const nextLogs = logs.value.concat(pendingLogs)
    pendingLogs = []
    pendingLogIds.clear()
    const trimmedLogs = nextLogs.length > MAX_LOGS ? nextLogs.slice(-MAX_LOGS) : nextLogs
    logs.value = trimmedLogs
    seenLogIds.clear()
    for (const log of trimmedLogs) {
      seenLogIds.add(log.id)
    }
  }

  function scheduleLogFlush(immediate = false) {
    if (immediate) {
      flushLogs()
      return
    }
    if (flushTimer) return
    flushTimer = setTimeout(() => {
      flushLogs()
    }, LOG_FLUSH_INTERVAL_MS)
  }

  function addLog(entry: LogEntry) {
    const normalizedEntry: StoredLogEntry = {
      ...entry,
      id: String(entry.id || `log-${Date.now()}-${++logSequence}`),
    }
    if (seenLogIds.has(normalizedEntry.id) || pendingLogIds.has(normalizedEntry.id)) {
      return
    }
    pendingLogs.push(normalizedEntry)
    pendingLogIds.add(normalizedEntry.id)
    scheduleLogFlush(pendingLogs.length >= LOG_IMMEDIATE_FLUSH_SIZE)
  }

  function clearLogs() {
    pendingLogs = []
    seenLogIds.clear()
    pendingLogIds.clear()
    if (flushTimer) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
    logs.value = []
  }

  function applyTheme(nextTheme: 'dark' | 'light') {
    theme.value = nextTheme
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_theme', nextTheme)
      document.documentElement.classList.toggle('dark', nextTheme === 'dark')
      document.body.classList.toggle('theme-light', nextTheme === 'light')
    }
  }

  function initTheme() {
    let initial: 'dark' | 'light' = 'dark'
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('app_theme')
      if (saved === 'light' || saved === 'dark') initial = saved
    }
    applyTheme(initial)
  }

  function toggleTheme() {
    applyTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  async function fetchPlatforms() {
    try {
      const { data } = await platformApi.list()
      platforms.value = data
    } catch {}
  }

  async function fetchStats() {
    try {
      const { data } = await statsApi.get(currentPlatform.value)
      stats.value = data
      if (data.platforms) {
        platforms.value = data.platforms
      }
    } catch {}
  }

  async function startTask(
    count: number,
    interval: number,
    concurrency = 1,
    mode: 'parallel' | 'pipeline' = 'parallel',
    intervalMin = 0,
    intervalMax = 0
  ) {
    await taskApi.start(
      count,
      interval,
      concurrency,
      currentPlatform.value,
      mode,
      intervalMin,
      intervalMax
    )
    await fetchStats()
  }

  async function stopTask() {
    const p = platforms.value.find(p => p.id === currentPlatform.value)
    if (p) p.running = false
    await taskApi.stop(currentPlatform.value)
    await fetchStats()
  }

  return {
    logs, stats, liveLog, currentPlatform, platforms, theme,
    addLog, clearLogs, fetchPlatforms, fetchStats, startTask, stopTask, initTheme, toggleTheme
  }
})
