# 服务端使用说明

## 环境要求

- Python 3.8+
- 网络可达（Kindle 和服务端在同一局域网）

## 安装步骤

```bash
cd server
pip install -r requirements.txt
```

## 启动服务端

```bash
cd server
python main.py
```

服务将在 `http://0.0.0.0:8080` 运行。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/events` | 获取所有事件 |
| POST | `/api/events` | 创建事件 |
| PUT | `/api/events/{id}` | 更新事件 |
| DELETE | `/api/events/{id}` | 删除事件 |
| GET | `/api/sync` | 增量同步 |

## 示例请求

```bash
# 创建事件
curl -X POST http://localhost:8080/api/events \
  -H "Content-Type: application/json" \
  -d '{"title":"团队会议","date":"2026-05-20","time":"10:00","priority":"important"}'

# 获取所有事件
curl http://localhost:8080/api/events

# 增量同步
curl "http://localhost:8080/api/sync?since=2026-05-19T00:00:00"
```

## 配置

在 `kindle/config.py` 中修改 `SERVER_URL` 为实际服务端地址。

## 部署建议

- **电脑**: 直接运行，保持电脑开机
- **树莓派**: 配置开机自启，适合 24小时运行
- **NAS**: 容器化部署