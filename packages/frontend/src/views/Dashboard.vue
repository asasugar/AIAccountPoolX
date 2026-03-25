<template>
  <div class="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30">
    <aside class="w-[300px] shrink-0 flex flex-col border-r border-slate-800/50 bg-slate-900/30 backdrop-blur-sm relative z-20">
      <Sidebar />
    </aside>

    <main class="flex-1 min-w-0 flex flex-col bg-slate-950/50 relative z-10">
      <LogViewer />
    </main>

    <div
      class="w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-indigo-500/30 transition-colors"
      @mousedown="startResize"
    ></div>

    <aside
      class="shrink-0 flex flex-col border-l border-slate-800/50 bg-slate-900/30 backdrop-blur-sm relative z-20"
      :style="{ width: `${rightPanelWidth}px` }"
    >
      <TokenPanel />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import LogViewer from '../components/LogViewer.vue'
import TokenPanel from '../components/TokenPanel.vue'

const MIN_RIGHT_WIDTH = 300
const MAX_RIGHT_WIDTH = 980
const rightPanelWidth = ref(350)
let resizing = false

function clampWidth(v: number) {
  return Math.min(MAX_RIGHT_WIDTH, Math.max(MIN_RIGHT_WIDTH, v))
}

function startResize() {
  resizing = true
  document.body.style.userSelect = 'none'
}

function onMouseMove(e: MouseEvent) {
  if (!resizing) return
  const nextWidth = window.innerWidth - e.clientX
  rightPanelWidth.value = clampWidth(nextWidth)
}

function stopResize() {
  if (!resizing) return
  resizing = false
  document.body.style.userSelect = ''
  localStorage.setItem('right_panel_width', String(rightPanelWidth.value))
}

onMounted(() => {
  const saved = Number(localStorage.getItem('right_panel_width') || 350)
  rightPanelWidth.value = clampWidth(Number.isFinite(saved) ? saved : 350)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', stopResize)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', stopResize)
  document.body.style.userSelect = ''
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
