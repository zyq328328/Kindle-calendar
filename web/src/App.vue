<template>
  <div class="app">
    <header class="header">
      <div class="brand">
        <span class="logo">📅</span>
        <h1>Kindle 日历管理</h1>
      </div>
      <div class="header-right">
        <span class="server-status" :class="connected ? 'online' : 'offline'">
          {{ connected ? 'Kindle 已连接' : 'Kindle 未连接' }}
        </span>
      </div>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCalendarStore } from './stores/calendar'

const calendarStore = useCalendarStore()
const connected = ref(false)

onMounted(async () => {
  connected.value = await calendarStore.checkHealth()
  await calendarStore.fetchEvents()
  await calendarStore.fetchEventsTree()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; }
.app { min-height: 100vh; }
.header { background: #1a1a2e; color: #fff; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; }
.brand { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 22px; }
.header h1 { font-size: 18px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 16px; }
.server-status { font-size: 13px; padding: 4px 12px; border-radius: 12px; }
.server-status.online { background: #4ade80; color: #000; }
.server-status.offline { background: #f87171; color: #fff; }
.main { padding: 24px; }
</style>
