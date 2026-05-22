# Kindle Calendar

Kindle 7 电子墨水屏智能日历，支持多视图切换、习惯打卡和 Web 管理后台。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│  Kindle 7 (192.168.10.72)                                   │
│  ┌─────────────┐    render + display    ┌──────────────┐  │
│  │ plan_a_main │ ─── PIL 渲染图 ────→  │ eips /dev/fb0 │  │
│  │  (KOReader)  │ ←── 触摸事件 ───────  │  (电子墨水屏) │  │
│  └─────────────┘                        └──────────────┘  │
│         ↓ fetch /api/events                                          │
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
│  │ Vue Web      │  ←─── 管理后台 (添加/编辑/打卡/下发)          │
│  │ 管理后台     │                                              │
│  └──────────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
server/          FastAPI 服务端
  main.py        API 入口
  models.py      Pydantic 数据模型
  database.py    SQLite 封装

web/             Vue 3 前端（Web 管理后台）
  src/
    views/ManageView.vue   管理界面
    api/events.js          API 调用
    stores/calendar.js     Pinia 状态管理

kindle/          Kindle 端脚本（需上传到设备）
  plan_a_main.py       主程序（触摸+渲染+视图切换）
  calendar_renderer.py  PIL 渲染器

plan_b/          已废弃的方案（保留参考）
```

## 视图说明

| 视图 | 说明 |
|------|------|
| 日视图（day） | 单日详细日程 |
| 三日视图（three_day） | 今日 + 未来 2 天 |
| 四象限（todo） | 重要×紧急 分四象限 |
| 习惯（habit） | 习惯打卡列表 |

## 四象限优先级

- Q1（重要+紧急）红色
- Q2（重要+非紧急）蓝色
- Q3（紧急+非重要）橙色
- Q4（绿色）

## 习惯重复规则

`none` / `daily` / `weekdays` / `weekly` / `monthly`

## API

- `GET /api/events?start=&end=` 获取事件（含习惯展开）
- `POST /api/events` 创建事件
- `PUT /api/events/{id}` 更新事件
- `POST /api/habits/{id}/checkin?date=YYYY-MM-DD` 习惯打卡
- `GET /` Web 管理后台

## 开发

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8082

cd web
npm install
npm run dev   # 开发
npm run build # 生产构建
```
