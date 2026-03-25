<template>
  <div>
    <Dashboard />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import Dashboard from './views/Dashboard.vue'
import { useAppStore } from './stores/app'
import { createLogWebSocket } from './api'

const store = useAppStore()
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout>

function connect() {
  ws = createLogWebSocket((data) => {
    store.addLog(data)
  })
  ws.onclose = () => {
    reconnectTimer = setTimeout(connect, 3000)
  }
  ws.onerror = () => {
    ws?.close()
  }
}

onMounted(() => {
  store.initTheme()
  connect()
})

onUnmounted(() => {
  clearTimeout(reconnectTimer)
  ws?.close()
})
</script>
