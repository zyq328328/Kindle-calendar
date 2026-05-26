<template>
  <div class="cal-layout">
    <!-- 左侧小型日历 -->
    <aside class="cal-sidebar">
      <div class="month-nav">
        <button @click="prevMonth">&lt;</button>
        <span class="month-label">{{ year }}年{{ month.toString().padStart(2,'0') }}月</span>
        <button @click="nextMonth">&gt;</button>
        <button @click="goToday" class="today-btn">今天</button>
      </div>
      <div class="weekday-row">
        <span v-for="d in ['一','二','三','四','五','六','日']" :key="d" class="weekday">{{ d }}</span>
      </div>
      <div class="days-grid">
        <div
          v-for="cell in calendarCells"
          :key="cell.key"
          class="day-cell"
          :class="{ 'other-month': !cell.inMonth, 'is-today': cell.isToday, 'selected': cell.dateStr === selectedDate }"
          @click="selectDate(cell)"
        >
          <span class="day-number">{{ cell.day }}</span>
          <!-- 横条：跨多天的待办事项 -->
          <div class="bars-area">
            <div
              v-for="bar in (cell.bars || [])"
              :key="bar.id"
              class="event-bar"
              :class="bar.type"
              :style="barStyle(bar, cell)"
            ></div>
          </div>
          <!-- 单天事件点 -->
          <div class="event-dots">
            <span v-for="ev in (cell.dots || []).slice(0, 3)" :key="ev.id" class="event-dot" :class="ev.type"></span>
            <span v-if="(cell.dots || []).length > 3" class="more">+{{ cell.dots.length - 3 }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧当日事项 -->
    <section class="day-panel">
      <div class="day-panel-header">
        <h3>{{ selectedDate || '选择日期' }}</h3>
        <button @click="openAdd" class="add-btn">+ 添加事项</button>
      </div>

      <div v-if="!selectedDate" class="no-date">← 请在左侧选择日期</div>
      <div v-else-if="rootEvents.length === 0" class="no-events">
        <p>当日无事项</p>
        <button @click="openAdd" class="add-btn">+ 添加事项</button>
      </div>
      <div v-else class="event-list">
        <template v-for="ev in rootEvents" :key="ev.id">
          <!-- 父事件卡片 -->
          <div class="event-card" :class="{ completed: ev.completed }">
            <div class="ev-left">
              <span class="ev-title" :class="{ done: ev.completed }">
                <span v-if="ev.completed" class="done-icon">✓</span>
                {{ ev.title }}
              </span>
              <span class="ev-meta">
                <span class="ev-type-badge" :class="ev.type">{{ typeLabel(ev.type) }}</span>
                <span v-if="ev.time" class="ev-time">{{ ev.time }}</span>
                <!-- 待办显示日期区间 -->
                <span v-if="ev.type === 'todo' && ev.start_date && ev.end_date" class="ev-duration">
                  {{ ev.start_date }} ~ {{ ev.end_date }}
                </span>
                <span v-if="ev.completed && ev.last_completed_date" class="done-date">✓ {{ ev.last_completed_date }}</span>
              </span>
              <!-- 子事项列表 -->
              <div v-if="childEvents[ev.id] && childEvents[ev.id].length" class="child-list">
                <div
                  v-for="child in childEvents[ev.id]"
                  :key="child.id"
                  class="event-card child-card"
                  :class="{ completed: child.completed }"
                >
                  <div class="ev-left">
                    <span class="ev-title child-title" :class="{ done: child.completed }">
                      <span v-if="child.completed" class="done-icon">✓</span>
                      {{ child.title }}
                    </span>
                    <span class="ev-meta">
                      <span class="ev-type-badge" :class="child.type">{{ typeLabel(child.type) }}</span>
                      <span v-if="child.time" class="ev-time">{{ child.time }}</span>
                      <span v-if="child.type === 'todo' && child.start_date && child.end_date" class="ev-duration">
                        {{ child.start_date }} ~ {{ child.end_date }}
                      </span>
                      <span v-if="child.completed && child.last_completed_date" class="done-date">✓ {{ child.last_completed_date }}</span>
                    </span>
                  </div>
                  <div class="ev-actions">
                    <button v-if="child.type === 'habit'" @click="checkin(child)" :class="{ checked: child.completed }">
                      {{ child.completed ? '✓ 已打卡' : '打卡' }}
                    </button>
                    <button v-else-if="child.type !== 'schedule'" @click="toggleDone(child)">{{ child.completed ? '取消' : '完成' }}</button>
                    <template v-if="child.type !== 'schedule'">
                      <button @click="openEdit(child)">编辑</button>
                      <button @click="remove(child.id)" class="del">删除</button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            <div class="ev-actions ev-actions-right">
              <button v-if="ev.type === 'habit'" @click="checkin(ev)" :class="{ checked: ev.completed }">
                {{ ev.completed ? '✓ 已打卡' : '打卡' }}
              </button>
              <button v-else-if="ev.type !== 'schedule'" @click="toggleDone(ev)">{{ ev.completed ? '取消' : '完成' }}</button>
              <template v-if="ev.type !== 'schedule'">
                <button @click="openEdit(ev)">编辑</button>
                <button @click="remove(ev.id)" class="del">删除</button>
              </template>
            </div>
          </div>
        </template>
      </div>
    </section>

    <!-- 弹窗：添加/编辑 -->
    <div class="modal" v-if="showModal">
      <div class="modal-backdrop" @click="showModal = false"></div>
      <div class="modal-box">
        <h3>{{ editing ? '编辑事项' : '添加事项' }}</h3>
        <div class="form-group">
          <label>标题 *</label>
          <input v-model="form.title" placeholder="事项标题" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>日期</label>
            <input v-model="form.date" type="date" />
          </div>
          <div class="form-group">
            <label>时间</label>
            <input v-model="form.time" type="time" placeholder="可选" />
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
          <div class="form-group">
            <label>父任务</label>
            <select v-model="form.parent_id">
              <option :value="null">（顶级任务）</option>
              <option v-for="ev in parentOptions" :key="ev.id" :value="ev.id">{{ ev.title }}</option>
            </select>
          </div>
        </div>
        <!-- 重复周期（仅日程和习惯） -->
        <div class="form-row" v-if="form.type === 'schedule' || form.type === 'habit'">
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
          <div class="form-group" v-if="form.recurrence_rule !== 'none'">
            <label>开始日期</label>
            <input v-model="form.start_date" type="date" />
          </div>
          <div class="form-group" v-if="form.recurrence_rule !== 'none'">
            <label>结束日期</label>
            <input v-model="form.end_date" type="date" placeholder="留空表示无限重复" />
          </div>
        </div>
        <!-- 持续时间（待办专用） -->
        <div class="form-row" v-if="form.type === 'todo'">
          <div class="form-group">
            <label>开始日期</label>
            <input v-model="form.start_date" type="date" />
          </div>
          <div class="form-group">
            <label>结束日期</label>
            <input v-model="form.end_date" type="date" />
          </div>
        </div>
        <!-- 重要性 + 紧急性（与后端统一：两个独立字段） -->
        <div class="form-row">
          <div class="form-group">
            <label>重要性</label>
            <select v-model="form.importance">
              <option value="important">重要</option>
              <option value="not_important">非重要</option>
            </select>
          </div>
          <div class="form-group">
            <label>紧急性</label>
            <select v-model="form.urgency">
              <option value="urgent">紧急</option>
              <option value="not_urgent">非紧急</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>描述</label>
          <input v-model="form.description" placeholder="可选" />
        </div>
        <div class="modal-actions">
          <button @click="showModal = false">取消</button>
          <button @click="save" class="primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useCalendarStore } from '../stores/calendar'

const store = useCalendarStore()
const year = ref(new Date().getFullYear())
const month = ref(new Date().getMonth() + 1)
const selectedDate = ref(new Date().toISOString().substring(0, 10))
const showModal = ref(false)
const editing = ref(null)
const form = ref({})

onMounted(() => fetchEvents())

const fetchEvents = () => {
  const start = `${year.value}-${month.value.toString().padStart(2,'0')}-01`
  const lastDay = new Date(year.value, month.value, 0).getDate()
  const end = `${year.value}-${month.value.toString().padStart(2,'0')}-${lastDay}`
  return store.fetchEventsRange(start, end)
}

watch([year, month], fetchEvents)

// ---- 父子结构 ----
// childEvents 返回 Map<parentId, children[]>，筛选规则：
// 1. 子任务在选中日期有记录（ev.date === selectedDate）
// 2. 若子任务 recurrence_rule !== 'none'（每日等重复），则选中日期须在 start~end 有效期内
// 3. 父任务 interval 覆盖选中日期
const childEvents = computed(() => {
  if (!selectedDate.value) return {}
  const map = {}
  for (const ev of store.events) {
    if (!ev.parent_id) continue
    // 子任务在选中日期必须有记录
    // 若 recurrence_rule !== 'none'（每日等重复），则选中日期须在 start~end 有效期内
    // 若 recurrence_rule === 'none' 但有明确的 start~end 区间，也应在区间内每天都显示
    if (ev.date !== selectedDate.value) {
      // 跨天检查：若子任务有区间，且选中日期在区间内，则显示
      const childStart = ev.start_date || ev.date
      const childEnd = ev.end_date || ev.date
      if (selectedDate.value < childStart || selectedDate.value > childEnd) continue
    }
    const parent = store.events.find(p => p.id === ev.parent_id)
    if (!parent) continue
    // 父任务是长周期待办，检查父任务 interval 是否覆盖选中日期
    if (parent.type === 'todo' && parent.start_date && parent.end_date && parent.start_date !== parent.end_date) {
      if (selectedDate.value < parent.start_date || selectedDate.value > parent.end_date) continue
    }
    // 父任务是普通事件，检查 date
    if (parent.type !== 'todo' && parent.date !== selectedDate.value) continue
    if (parent.type === 'todo' && (!parent.start_date || !parent.end_date || parent.start_date === parent.end_date) && parent.date !== selectedDate.value) continue
    if (!map[ev.parent_id]) map[ev.parent_id] = []
    map[ev.parent_id].push(ev)
  }
  return map
})

// 顶级事件（无 parent_id），按 id 去重
// 规则：非待办按 date 精确匹配；待办若为多天区间则区间内每天都显示，单天待办按 date 匹配
const rootEvents = computed(() => {
  if (!selectedDate.value) return []
  const seen = new Set()
  return store.events.filter(e => {
    if (e.parent_id) return false
    if (seen.has(e.id)) return false
    let match = false
    if (e.type !== 'todo') {
      match = e.date === selectedDate.value
    } else if (e.start_date && e.end_date && e.start_date !== e.end_date) {
      match = e.start_date <= selectedDate.value && selectedDate.value <= e.end_date
    } else {
      match = e.date === selectedDate.value
    }
    if (match) seen.add(e.id)
    return match
  })
})

// ---- 日历格子 ----
const calendarCells = computed(() => {
  const cells = []
  const firstDay = new Date(year.value, month.value - 1, 1)
  let startWeekday = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1
  const prevDays = new Date(year.value, month.value - 1, 0).getDate()
  // 上月残余格子
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = prevDays - i
    cells.push({ key: `prev-${d}`, day: d, inMonth: false, isToday: false, dots: [], bars: [], dateStr: null })
  }
  // 当月格子
  const lastDay = new Date(year.value, month.value, 0).getDate()
  const today = new Date()
  for (let d = 1; d <= lastDay; d++) {
    const isToday = today.getFullYear() === year.value && today.getMonth() + 1 === month.value && today.getDate() === d
    const dateStr = `${year.value}-${month.value.toString().padStart(2,'0')}-${d.toString().padStart(2,'0')}`
    const dayAll = store.events.filter(e => e.date === dateStr)
    // 单天事件：非待办，或待办但 start_date === end_date（同一天）
    const dots = dayAll.filter(e => e.type !== 'todo' || (e.start_date && e.end_date && e.start_date === e.end_date))
    // 跨多天待办：待办且有 start_date < end_date
    const bars = dayAll.filter(e => e.type === 'todo' && e.start_date && e.end_date && e.start_date !== e.end_date)
    cells.push({ key: dateStr, day: d, inMonth: true, isToday, dots, bars, dateStr })
  }
  // 下月占位格
  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    cells.push({ key: `next-${d}`, day: d, inMonth: false, isToday: false, dots: [], bars: [], dateStr: null })
  }
  return cells
})

// 待办横条样式
function barStyle(bar, cell) {
  const start = bar.start_date
  const end = bar.end_date
  const cellDate = cell.dateStr
  if (!start || !end || !cellDate || cellDate < start || cellDate > end) {
    return { display: 'none' }
  }
  const isStart = cellDate === start
  const isEnd = cellDate === end
  const style = { background: '#d97706' }
  if (isStart) style.borderRadius = '3px 0 0 3px'
  else if (isEnd) style.borderRadius = '0 3px 3px 0'
  else style.borderRadius = '0'
  return style
}

const parentOptions = computed(() => store.tree)

function prevMonth() {
  if (month.value === 1) { year.value--; month.value = 12 }
  else month.value--
}
function nextMonth() {
  if (month.value === 12) { year.value++; month.value = 1 }
  else month.value++
}
function goToday() {
  const t = new Date()
  year.value = t.getFullYear()
  month.value = t.getMonth() + 1
  selectedDate.value = new Date().toISOString().substring(0, 10)
}
function selectDate(cell) {
  if (!cell.inMonth) return
  selectedDate.value = cell.dateStr
}

function openAdd() {
  editing.value = null
  form.value = {
    title: '', date: selectedDate.value, time: '', type: 'schedule',
    importance: 'not_important', urgency: 'not_urgent', description: '',
    is_countdown: false, recurrence_rule: 'none',
    start_date: selectedDate.value, end_date: selectedDate.value,
    last_completed_date: '', parent_id: null
  }
  showModal.value = true
}
function openEdit(ev) {
  editing.value = ev.id
  form.value = { ...ev }
  showModal.value = true
}
async function save() {
  if (!form.value.title) return
  if (editing.value) {
    await store.updateEvent(editing.value, form.value)
  } else {
    await store.createEvent(form.value)
  }
  showModal.value = false
  await fetchEvents()
}
async function toggleDone(ev) {
  if (!ev || !ev.id) return
  await store.updateEvent(ev.id, { completed: !ev.completed })
  await fetchEvents()
}
async function checkin(ev) {
  await store.checkinHabit(ev.id, selectedDate.value)
  await fetchEvents()
}
async function remove(id) {
  if (!confirm('确认删除？')) return
  await store.deleteEvent(id)
  await fetchEvents()
}

function typeLabel(t) {
  return { schedule: '日程', todo: '待办', habit: '习惯' }[t] || t
}
</script>

<style scoped>
.cal-layout { display: flex; gap: 24px; max-width: 1100px; margin: 0 auto; align-items: flex-start; }

/* 左侧日历 */
.cal-sidebar { width: 300px; flex-shrink: 0; background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.month-nav { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.month-nav button { padding: 4px 10px; border: 1px solid #e2e8f0; background: #fff; border-radius: 6px; cursor: pointer; }
.today-btn { background: #1a1a2e; color: #fff; border-color: #1a1a2e; font-size: 12px; padding: 4px 8px; }
.month-label { font-size: 14px; font-weight: 600; min-width: 100px; text-align: center; }
.weekday-row { display: grid; grid-template-columns: repeat(7, 1fr); margin-bottom: 4px; }
.weekday { text-align: center; font-size: 11px; color: #64748b; font-weight: 600; padding: 4px 0; }
.days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
.day-cell { min-height: 40px; padding: 3px; border: 1px solid #f1f5f9; cursor: pointer; border-radius: 4px; display: flex; flex-direction: column; align-items: center; transition: background 0.1s; position: relative; }
.day-cell:hover { background: #f8fafc; }
.day-cell.other-month { background: #fafafa; }
.day-cell.other-month .day-number { color: #cbd5e1; }
.day-cell.is-today .day-number { background: #2563eb; color: #fff; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; }
.day-cell.selected { background: #eff6ff; border-color: #2563eb; }
.day-number { font-size: 12px; font-weight: 500; }

/* 待办横条 */
.bars-area { display: flex; flex-direction: column; gap: 1px; width: 100%; margin-top: 2px; }
.event-bar { height: 4px; background: #d97706; width: 100%; }
.event-bar.schedule { background: #2563eb; }
.event-bar.habit { background: #059669; }

/* 单天事件点 */
.event-dots { display: flex; flex-wrap: wrap; gap: 2px; justify-content: center; margin-top: 2px; }
.event-dot { width: 5px; height: 5px; border-radius: 50%; }
.event-dot.schedule { background: #2563eb; }
.event-dot.todo { background: #d97706; }
.event-dot.habit { background: #059669; }
.more { font-size: 9px; color: #94a3b8; }

/* 右侧面板 */
.day-panel { flex: 1; background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); min-height: 500px; }
.day-panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.day-panel-header h3 { font-size: 18px; }
.add-btn { background: #1a1a2e; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.no-date, .no-events { color: #94a3b8; font-size: 14px; text-align: center; padding: 40px 0; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.event-list { display: flex; flex-direction: column; gap: 10px; }
.event-card { display: flex; justify-content: space-between; align-items: flex-start; padding: 12px 16px; background: #f8fafc; border-radius: 10px; border: 1px solid #f1f5f9; }
.event-card.completed { opacity: 0.55; }
.ev-left { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.ev-title { font-size: 15px; font-weight: 500; display: flex; align-items: center; gap: 6px; }
.ev-title.done { text-decoration: line-through; color: #94a3b8; }
.done-icon { color: #059669; }
.ev-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #64748b; flex-wrap: wrap; }
.ev-type-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.ev-type-badge.schedule { background: #dbeafe; color: #2563eb; }
.ev-type-badge.todo { background: #fef3c7; color: #d97706; }
.ev-type-badge.habit { background: #d1fae5; color: #059669; }
.ev-time { color: #94a3b8; }
.ev-duration { color: #d97706; font-weight: 500; }
.done-date { color: #059669; }
.ev-actions { display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0; }
.ev-actions button { padding: 5px 10px; border: 1px solid #e2e8f0; background: #fff; border-radius: 6px; cursor: pointer; font-size: 12px; }
.ev-actions button.del { color: #ef4444; border-color: #fecaca; }
.ev-actions button.checked { background: #059669; color: #fff; border-color: #059669; }

/* 子事项缩进 */
.child-list { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; padding-left: 16px; border-left: 2px solid #e2e8f0; }
.child-card { background: #fff; padding: 8px 12px; border-radius: 8px; }
.child-title { font-size: 14px; }

/* 弹窗 */
.modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.4); }
.modal-box { position: relative; background: #fff; border-radius: 14px; padding: 28px; width: 480px; max-width: 95vw; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.modal-box h3 { margin-bottom: 20px; font-size: 18px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; color: #64748b; margin-bottom: 5px; }
.form-group input, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
.form-row { display: flex; gap: 12px; margin-bottom: 14px; }
.form-row .form-group { flex: 1; margin-bottom: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.modal-actions button { padding: 9px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; border: 1px solid #e2e8f0; background: #fff; }
.modal-actions button.primary { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
</style>
