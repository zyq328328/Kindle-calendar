import { defineStore } from 'pinia'
import { ref } from 'vue'
import { eventApi } from '../api/events'

export const useCalendarStore = defineStore('calendar', () => {
  const events = ref([])
  const tree = ref([])      // 嵌套树结构（含 children）
  const loading = ref(false)

  async function checkHealth() {
    try {
      const r = await eventApi.health()
      return !!(r && r.status === 'healthy')
    } catch {
      return false
    }
  }

  async function fetchEvents() {
    loading.value = true
    try {
      events.value = await eventApi.list()
    } finally {
      loading.value = false
    }
  }

  async function fetchEventsRange(start, end) {
    loading.value = true
    try {
      events.value = await eventApi.list(start, end)
    } finally {
      loading.value = false
    }
  }

  async function fetchEventsTree() {
    loading.value = true
    try {
      tree.value = await eventApi.tree()
    } finally {
      loading.value = false
    }
  }

  async function createEvent(data) {
    const created = await eventApi.create(data)
    events.value.push(created)
    // 重新获取树
    await fetchEventsTree()
    return created
  }

  async function updateEvent(id, data) {
    const updated = await eventApi.update(id, data)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) events.value[idx] = updated
    await fetchEventsTree()
    return updated
  }

  async function deleteEvent(id) {
    await eventApi.delete(id)
    events.value = events.value.filter(e => e.id !== id)
    await fetchEventsTree()
  }

  async function checkinHabit(id, date) {
    const updated = await eventApi.checkin(id, date)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) events.value[idx] = { ...events.value[idx], ...updated, completed: true }
    await fetchEventsTree()
  }

  return { events, tree, loading, checkHealth, fetchEvents, fetchEventsRange, fetchEventsTree, createEvent, updateEvent, deleteEvent, checkinHabit }
})
