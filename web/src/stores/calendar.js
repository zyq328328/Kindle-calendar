import { defineStore } from 'pinia'
import { ref } from 'vue'
import { eventApi } from '../api/events'

export const useCalendarStore = defineStore('calendar', () => {
  const events = ref([])
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

  async function createEvent(data) {
    const created = await eventApi.create(data)
    events.value.push(created)
    return created
  }

  async function updateEvent(id, data) {
    const updated = await eventApi.update(id, data)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) events.value[idx] = updated
    return updated
  }

  async function deleteEvent(id) {
    await eventApi.delete(id)
    events.value = events.value.filter(e => e.id !== id)
  }

  async function checkinHabit(id, date) {
    const updated = await eventApi.checkin(id, date)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) events.value[idx] = { ...events.value[idx], ...updated, completed: true }
  }

  return { events, loading, checkHealth, fetchEvents, createEvent, updateEvent, deleteEvent, checkinHabit }
})
