<template>
  <div class="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30">
    <!-- 左侧导航 -->
    <aside class="w-[300px] shrink-0 flex flex-col border-r border-slate-800/50 bg-slate-900/30 backdrop-blur-sm relative z-20">
      <Sidebar />
    </aside>

    <!-- 中间日志 (自适应宽度) -->
    <main class="flex-1 min-w-0 flex flex-col bg-slate-950/50 relative z-10">
      <LogViewer />
    </main>

    <!-- 右侧面板 (固定宽度) -->
    <aside class="w-[600px] shrink-0 flex flex-col border-l border-slate-800/50 bg-slate-900/30 backdrop-blur-sm relative z-20">
      <TokenPanel />
    </aside>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '../components/Sidebar.vue'
import LogViewer from '../components/LogViewer.vue'
import TokenPanel from '../components/TokenPanel.vue'
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
