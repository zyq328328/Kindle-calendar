<template>
  <div class="manage-view">
    <div class="top-bar">
      <h2>日历管理</h2>
      <div class="actions">
        <button @click="checkSync" :class="{ ok: synced }">
          {{ synced ? '✓ 已同步' : '同步 Kindle' }}
        </button>
        <button @click="openAdd()" class="primary">+ 添加日程</button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filters">
      <input v-model="filterText" placeholder="搜索日程..." class="search" />
      <select v-model="filterType">
        <option value="">全部类型</option>
        <option value="schedule">日程</option>
        <option value="todo">待办</option>
        <option value="habit">习惯</option>
      </select>
      <select v-model="filterImportance">
        <option value="">全部重要性</option>
        <option value="important">重要</option>
        <option value="not_important">非重要</option>
      </select>
      <select v-model="filterUrgency">
        <option value="">全部紧急性</option>
        <option value="urgent">紧急</option>
        <option value="not_urgent">非紧急</option>
      </select>
    </div>

    <!-- 事件列表（树形） -->
    <div class="event-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="!flatFiltered.length" class="empty">暂无日程，点上方「添加日程」</div>
      <template v-else>
        <div
          v-for="ev in flatFiltered"
          :key="ev.id"
          class="event-card"
          :class="{ completed: ev.completed, 'is-child': ev.depth > 0 }"
          :style="{ marginLeft: ev.depth * 24 + 'px' }"
        >
          <div class="ev-left">
            <span class="quadrant-badge" :class="evQuadrant(ev)">{{ evQuadrant(ev) }}</span>
            <div class="ev-info">
              <span class="ev-title">
                <span v-if="ev.depth > 0" class="child-indicator">└─ </span>
                {{ ev.title }}
              </span>
              <span class="ev-meta">
                <span v-if="ev.parent_id" class="parent-ref">→ 父任务 #{{ ev.parent_id }}</span>
                {{ ev.date }} {{ ev.time || '' }}
              </span>
            </div>
          </div>
          <div class="ev-right">
            <span class="ev-type-badge" :class="ev.type">{{ typeLabel(ev.type) }}</span>
            <button v-if="ev.type === 'habit'" @click="checkin(ev)" :class="{ checked: ev.completed }">
              {{ ev.completed ? '✓ 已打卡' : '打卡' }}
            </button>
            <button @click="toggleDone(ev)">{{ ev.completed ? '取消' : '完成' }}</button>
            <button @click="openEdit(ev)">编辑</button>
            <button @click="remove(ev.id)" class="del">删除</button>
          </div>
        </div>
      </template>
    </div>

    <!-- 弹窗 -->
    <div class="modal-overlay" v-if="showModal" @click.self="closeModal">
      <div class="modal">
        <h3>{{ editing ? '编辑日程' : '添加日程' }}</h3>
        <div class="form-group">
          <label>标题 *</label>
          <input v-model="form.title" placeholder="日程标题" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>日期</label>
            <input v-model="form.date" type="date" />
          </div>
          <div class="form-group">
            <label>时间</label>
            <input v-model="form.time" type="time" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>类型</label>
            <select v-model="form.type">
              <option value="schedule">日程</option>
              <option value="todo">待办</option>
              <option value="habit">习惯</option>
            </select>
          </div>
          <!-- 父任务选择 -->
          <div class="form-group">
            <label>父任务</label>
            <select v-model="form.parent_id">
              <option :value="null">（顶级任务）</option>
              <option v-for="p in parentOptions" :key="p.id" :value="p.id">
                {{ p.title }} ({{ p.date }})
              </option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group" v-if="form.type !== 'habit'">
            <label>重要性</label>
            <select v-model="form.importance">
              <option value="not_important">非重要</option>
              <option value="important">重要</option>
            </select>
          </div>
          <div class="form-group" v-if="form.type !== 'habit'">
            <label>紧急性</label>
            <select v-model="form.urgency">
              <option value="not_urgent">非紧急</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
        </div>
        <!-- 习惯重复周期 -->
        <div class="form-row" v-if="form.type === 'habit'">
          <div class="form-group">
            <label>重复周期</label>
            <select v-model="form.recurrence_rule">
              <option value="none">不重复</option>
              <option value="daily">每天</option>
              <option value="weekdays">工作日</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
          <div class="form-group">
            <label>开始日期</label>
            <input v-model="form.start_date" type="date" />
          </div>
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="form.description" rows="2"></textarea>
        </div>
        <div class="form-group">
          <label>提醒</label>
          <select v-model="form.is_countdown">
            <option :value="false">关闭</option>
            <option :value="true">开启倒计时</option>
          </select>
        </div>
        <div class="modal-actions">
          <button @click="closeModal">取消</button>
          <button @click="save" class="primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCalendarStore } from '../stores/calendar'

const store = useCalendarStore()
const showModal = ref(false)
const editing = ref(null)
const filterText = ref('')
const filterType = ref('')
const filterImportance = ref('')
const filterUrgency = ref('')
const synced = ref(true)

const form = ref({ title: '', date: '', time: '', type: 'schedule', importance: 'not_important', urgency: 'not_urgent', description: '', is_countdown: false, recurrence_rule: 'none', start_date: '', last_completed_date: '', parent_id: null })

onMounted(() => { store.fetchEvents(); store.fetchEventsTree() })

// 将事件树扁平化，并附加 depth 用于缩进
const flatEvents = computed(() => {
  const result = []
  function flatten(events, depth) {
    for (const ev of events) {
      result.push({ ...ev, depth })
      if (ev.children && ev.children.length) {
        flatten(ev.children, depth + 1)
      }
    }
  }
  // 用 store.tree 而不是 store.events（tree 才有 children）
  if (store.tree && store.tree.length) {
    flatten(store.tree, 0)
  }
  return result
})

// parentOptions：可作为父任务的任务列表（不能是自己或自己的后代）
const parentOptions = computed(() => {
  if (!editing.value) {
    // 新建时，所有顶级任务（无 parent_id）都可以作为父任务
    return store.events.filter(e => e.parent_id === null || e.parent_id === undefined)
  }
  // 编辑时，排除自己和自己的后代
  const descendantIds = new Set()
  function collectDescendants(ev) {
    if (ev.children) ev.children.forEach(c => { descendantIds.add(c.id); collectDescendants(c) })
  }
  const self = store.events.find(e => e.id === editing.value.id)
  if (self) collectDescendants(self)
  return store.events.filter(e => e.id !== editing.value.id && !descendantIds.has(e.id))
})

const filteredEvents = computed(() => {
  return flatEvents.value.filter(e => {
    if (filterType.value && e.type !== filterType.value) return false
    if (filterImportance.value && e.importance !== filterImportance.value) return false
    if (filterUrgency.value && e.urgency !== filterUrgency.value) return false
    if (filterText.value && !e.title.includes(filterText.value)) return false
    return true
  })
})

// 同时满足搜索条件：搜索时包含子任务，筛选时也包含子任务
const flatFiltered = computed(() => {
  const fText = filterText.value
  const fType = filterType.value
  const fImp = filterImportance.value
  const fUrg = filterUrgency.value
  const result = []
  function flatten(events, depth) {
    for (const ev of events) {
      const evWithDepth = { ...ev, depth }
      const matchText = !fText || ev.title.includes(fText)
      const matchType = !fType || ev.type === fType
      const matchImp = !fImp || ev.importance === fImp
      const matchUrg = !fUrg || ev.urgency === fUrg
      if (matchText && matchType && matchImp && matchUrg) {
        result.push(evWithDepth)
      }
      if (ev.children && ev.children.length) {
        flatten(ev.children, depth + 1)
      }
    }
  }
  if (store.tree && store.tree.length) {
    flatten(store.tree, 0)
  }
  return result
})

function evQuadrant(ev) {
  const imp = ev.importance || 'not_important'
  const urg = ev.urgency || 'not_urgent'
  if (imp === 'important' && urg === 'urgent') return 'Q1'
  if (imp === 'important' && urg === 'not_urgent') return 'Q2'
  if (imp === 'not_important' && urg === 'urgent') return 'Q3'
  return 'Q4'
}

function typeLabel(t) {
  return { schedule: '日程', todo: '待办', habit: '习惯' }[t] || t
}

function openAdd() {
  editing.value = null
  form.value = { title: '', date: new Date().toISOString().substring(0, 10), time: '', type: 'schedule', importance: 'not_important', urgency: 'not_urgent', description: '', is_countdown: false, recurrence_rule: 'none', start_date: new Date().toISOString().substring(0, 10), last_completed_date: '', parent_id: null }
  showModal.value = true
}

function openEdit(ev) {
  editing.value = ev
  form.value = { ...ev }
  showModal.value = true
}

function closeModal() { showModal.value = false; editing.value = null }

async function save() {
  if (!form.value.title.trim()) return
  if (editing.value) {
    await store.updateEvent(editing.value.id, form.value)
  } else {
    await store.createEvent(form.value)
  }
  synced.value = false
  // 重新获取事件树
  await store.fetchEventsTree()
  closeModal()
}

async function checkin(ev) {
  const today = new Date().toISOString().substring(0, 10)
  await store.checkinHabit(ev.id, today)
  synced.value = false
}

async function toggleDone(ev) {
  await store.updateEvent(ev.id, { completed: !ev.completed })
  synced.value = false
}

async function remove(id) {
  if (!confirm('删除这条日程？')) return
  await store.deleteEvent(id)
  synced.value = false
}

async function checkSync() {
  await store.fetchEvents()
  synced.value = true
}
</script>

<style scoped>
.manage-view { max-width: 800px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top-bar h2 { font-size: 22px; }
.actions { display: flex; gap: 12px; }
.actions button { padding: 8px 18px; border: 1px solid #e2e8f0; background: #fff; border-radius: 8px; cursor: pointer; font-size: 14px; }
.actions button.primary { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
.actions button.ok { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
.filters { display: flex; gap: 10px; margin-bottom: 20px; }
.search { flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
.filters select { padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
.event-list { display: flex; flex-direction: column; gap: 10px; }
.loading, .empty { text-align: center; padding: 40px; color: #94a3b8; }
.event-card { background: #fff; border-radius: 10px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); transition: margin-left 0.2s; }
.event-card.completed { opacity: 0.55; }
.event-card.is-child { background: #f8fafc; border-left: 3px solid #cbd5e1; }
.ev-left { display: flex; gap: 12px; align-items: center; }
.quadrant-badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; font-weight: 600; flex-shrink: 0; }
.quadrant-badge.Q1 { background: #fee2e2; color: #dc2626; }
.quadrant-badge.Q2 { background: #dbeafe; color: #2563eb; }
.quadrant-badge.Q3 { background: #fef3c7; color: #d97706; }
.quadrant-badge.Q4 { background: #f0fdf4; color: #16a34a; }
.ev-info { display: flex; flex-direction: column; gap: 3px; }
.ev-title { font-size: 15px; font-weight: 500; }
.child-indicator { color: #94a3b8; font-weight: 400; }
.ev-meta { font-size: 13px; color: #64748b; }
.parent-ref { color: #94a3b8; margin-right: 8px; }
.ev-right { display: flex; gap: 8px; align-items: center; }
.ev-type-badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.ev-type-badge.schedule { background: #dbeafe; color: #2563eb; }
.ev-type-badge.todo { background: #fef3c7; color: #d97706; }
.ev-type-badge.habit { background: #d1fae5; color: #059669; }
.ev-right button { padding: 5px 12px; border: 1px solid #e2e8f0; background: #fff; border-radius: 6px; cursor: pointer; font-size: 13px; }
.ev-right .del { color: #ef4444; border-color: #fecaca; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 460px; max-width: 95vw; }
.modal h3 { margin-bottom: 20px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; color: #64748b; margin-bottom: 4px; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.modal-actions button { padding: 8px 20px; border: 1px solid #e2e8f0; background: #fff; border-radius: 8px; cursor: pointer; }
.modal-actions button.primary { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
</style>
