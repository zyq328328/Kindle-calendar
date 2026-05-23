# Kindle Calendar

Kindle 7 电子墨水屏智能日历，支持多视图切换、习惯打卡和 Web 管理后台。

## 功能特性

- **多视图切换**：今日、单日（单日详细）、三日（今日+未来2天）、待办（习惯打卡）、四象限（重要×紧急矩阵）、设置
- **三种事件类型**：日程（schedule）、待办（todo）、习惯（habit）
- **重复事件**：支持每日、工作日、每周、每月重复，可选结束日期
- **四象限**：仅显示待办+习惯，按重要/紧急分四区
- **嵌套任务**：待办可无限嵌套子任务，树状展示
- **触摸交互**：点击 □ 可标记完成（三日视图/待办列表/四象限）
- **KUAL 入口**：在 KOReader 中通过 KUAL 菜单启动

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│  Kindle 7 (192.168.10.72)                                  │
│  ┌─────────────┐    render + display    ┌──────────────┐  │
│  │ plan_a_main │ ─── PIL 渲染图 ────→  │ eips /dev/fb0 │  │
│  │  (KOReader)  │ ←── 触摸事件 ───────  │  (电子墨水屏) │  │
│  └─────────────┘                        └──────────────┘  │
│         ↓ fetch /api/events/tree                                   │
└─────────┼───────────────────────────────────────────────────────┘
          │  HTTP (port 8082)
          ↓
┌─────────────────────────────────────────────────────────────┐
│  VM2 Server (192.168.188.7)                                  │
│  ┌──────────────┐    SQLite     ┌──────────────────────┐   │
│  │ FastAPI      │ ←──────────→  │ kindle_calendar.db   │   │
│  │ :8082        │               │ events / habits      │   │
│  └──────────────┘               └──────────────────────┘   │
│         ↓ static file                                               │
│  ┌──────────────┐                                              │
│  │ Vue Web      │  ←─── 管理后台 (添加/编辑/打卡/删除)          │
│  │ 管理后台     │                                              │
│  └──────────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

**核心设计**：Kindl 本地渲染 + 触摸，VM2 只提供 API 数据（Plan A）

## 目录结构

```
server/          FastAPI 服务端
  main.py        API 入口
  models.py      Pydantic 数据模型（Event, EventUpdate, EventTreeItem）
  database.py    SQLite 封装（expand_recurrence, get_event_tree 等）

web/             Vue 3 前端（Web 管理后台）
  src/
    views/ManageView.vue   管理界面（添加/编辑/删除/打卡）
    api/events.js          API 调用
    stores/calendar.js     Pinia 状态管理

kindle/          Kindle 端脚本（需上传到设备 /mnt/us/extensions/KindleCalendar/bin/）
  plan_a_main.py       主程序（触摸+渲染+视图切换）
  calendar_renderer.py  PIL 渲染器（各视图渲染函数）
```

## 视图说明

| 视图 | 导航名 | 说明 |
|------|--------|------|
| 今日（home） | 今日 | 进入默认视图，左侧时钟+右侧今日事件 |
| 单日（day） | 单日 | 单日详细日程，支持左右滑动切日 |
| 三日（three_day） | 三日 | 今日+未来2天，分【日程】【待办】两区，各4条 |
| 待办（habit） | 待办 | 习惯打卡列表，显示□完成框 |
| 四象限（quadrant） | 四象 | 重要×紧急矩阵，仅todo+habit |
| 设置 | 设置 | （预留） |

### 三日视图布局

- 每列 257px 宽（800÷3≈266，减去导航栏约 740px 可用）
- 左上角显示日期星期，左侧时间，右侧日程/待办
- 【日程】区：最多4条日程（时间+标题），无□
- 【待办】区：最多4条待办/习惯（有□，支持嵌套缩进），显示完成状态

### 四象限布局

| 重要+紧急（左上) | 重要+不紧急（右上） |
| 紧急+不重要（左下） | 不紧急+不重要（右下） |

标准 Eisenhower 矩阵，仅显示 todo + habit。

## 重复事件扩展方案

为解决 Kindle 端重复事件（每日习惯）无法在每一天显示的问题，采用 **display_dates** 方案：

1. **数据库层**：`expand_recurrence` 两遍算法，第一遍收集所有日期到 `all_dates`，第二遍生成 occurrence 每个都携带完整的 `display_dates` 列表
2. **API 层**：`get_event_tree` 返回树形结构，每个重复事件节点携带 `display_dates` 字段（含全部 271 个日期）
3. **Kindle 渲染层**：日期匹配改用 `_event_matches_date` 函数，先检查 `date` 字段，再用 `date_key in display_dates` 做 fallback

**关键字段**：

- `start_date`：习惯的开始日期
- `end_date`：习惯的结束日期（留空=无期限）
- `display_dates`：该事件所有应显示的日期列表（供 Kindle 过滤用）

## API

- `GET /api/events/tree` 获取事件树（含重复事件展开），推荐
- `GET /api/events?start=&end=` 获取扁平事件列表
- `POST /api/events` 创建事件
- `PUT /api/events/{id}` 更新事件
- `DELETE /api/events/{id}` 删除事件
- `POST /api/habits/{id}/checkin?date=YYYY-MM-DD` 习惯打卡
- `GET /api/health` 健康检查
- `GET /` Web 管理后台

## 数据库 Schema

```sql
events (
  id, title, description, date, time,
  importance, urgency,
  type,           -- schedule | todo | habit
  recurrence_rule,-- none | daily | weekdays | weekly | monthly
  start_date,     -- 习惯开始日期
  end_date,       -- 习惯结束日期（留空=无期限）
  display_dates,  -- (内部使用) 重复事件全部日期
  parent_id,      -- 父任务 ID，null=顶级
  completed, is_countdown, countdown_target,
  last_completed_date,
  created_at, updated_at
)
```

## 开发

```bash
# 服务端
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8082

# 前端
cd web
npm install
npm run dev   # 开发
npm run build # 生产构建

# 部署到 VM2
rsync -av --delete dist/ user@vm2:/opt/kindle-calendar/web/dist/
sudo cp server/database.py /opt/kindle-calendar/server/
systemctl restart kindle-calendar

# 同步到 Kindle
scp -i ~/.ssh/kindle_key kindle/calendar_renderer.py root@192.168.10.72:/mnt/us/extensions/KindleCalendar/bin/
```

## 触摸映射（Kindle 7）

- 物理屏幕 600×800 → 渲染画面 800×600
- 映射公式：`x_render = 800 - y_phys, y_render = x_phys`
- 右侧导航区：`x_render >= 740`

## 相关文档

- 架构设计：TODO
- 重复事件设计：server/database.py `expand_recurrence` 函数
- 触摸协议：Kindle 7 zforce2 红外触摸屏，EV_ABS type=3
