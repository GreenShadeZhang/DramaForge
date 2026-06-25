# DramaForge 原生部署指南

本文档适用于不使用 Docker 的原生部署。当前后端启动方式已经改为：一个 Uvicorn 进程同时启动 FastAPI API 和内嵌 arq Worker。

## 架构

原生部署需要三个长期运行的服务：

- Redis：任务队列。
- Backend：FastAPI API；启动时会自动启动媒体生成 Worker。
- Frontend：Vue 构建后的静态站点，由 Nginx、Caddy、IIS 或其他静态服务托管。

图片和视频生成流程：

1. 用户请求进入 FastAPI。
2. FastAPI 创建媒体任务，状态为 `queued`，并写入 Redis 队列。
3. 同一个 Uvicorn 进程里的 arq Worker 从 Redis 消费任务。
4. Worker 调用 AI 接口，完成后更新数据库任务状态和结果资源。

## 环境要求

- Python 3.11 或更高版本。
- Node.js 20 或更高版本。
- Redis 7 或兼容版本。
- FFmpeg，视频处理需要。

Windows 原生部署建议确认命令可用：

```powershell
python --version
node --version
npm --version
ffmpeg -version
```

## 配置

复制环境变量文件：

```powershell
Copy-Item .env.example .env
```

原生部署时，Redis 通常使用本机地址：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

至少还需要配置：

```env
LAOZHANG_API_KEY=your-api-key
LAOZHANG_BASE_URL=https://api.laozhang.ai/v1
DATABASE_URL=sqlite+aiosqlite:///./storage/dramaforge.db
JWT_SECRET_KEY=change-this-to-a-random-string
SECRET_KEY=change-this-to-a-random-string
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

生产环境请把 `DEBUG=false`，并把 `CORS_ORIGINS` 改为真实前端域名。

## 启动 Redis

Windows 上如果 Redis 已安装为服务：

```powershell
redis-cli ping
```

返回 `PONG` 表示可用。

如果 Redis 不在本机，确保 `.env` 的 `REDIS_URL` 指向实际地址，并且后端机器可以访问该端口。

## 启动后端

安装依赖：

```powershell
cd dramaForge_bac
pip install -r requirements.txt
```

启动后端：

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

正常启动日志中应出现：

```text
Embedded media generation worker started
```

看到这行日志表示 arq Worker 已随 FastAPI 一起启动。正常单机原生部署不需要再单独运行 `arq app.tasks.WorkerSettings`。

如果之前已经手动启动过独立的 `arq app.tasks.WorkerSettings` 进程，切换到当前启动方式后请停止旧的独立 arq 进程，避免同一机器上出现额外队列消费者。

## 启动前端

开发环境：

```powershell
cd dramaForge_web
npm install
npm run dev
```

生产构建：

```powershell
cd dramaForge_web
npm install
npm run build
```

构建产物位于 `dramaForge_web/dist`。将该目录交给 Nginx、Caddy、IIS 或其他静态服务托管，并把 API 请求代理到后端 `http://127.0.0.1:8000`。

## 生产进程守护

### Windows

可以使用 NSSM、Windows 服务、任务计划程序或进程管理器守护后端命令：

```powershell
cd E:\project\DramaForge\dramaForge_bac
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

关键要求：

- 工作目录必须是 `dramaForge_bac`，这样相对路径数据库 `./storage/dramaforge.db` 才会落在后端目录下。
- 服务账号必须能读取项目 `.env`，并能写入 `dramaForge_bac/storage`。
- Redis 必须先于后端可用。

### Linux systemd 示例

```ini
[Unit]
Description=DramaForge Backend
After=network.target redis.service

[Service]
Type=simple
WorkingDirectory=/opt/DramaForge/dramaForge_bac
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/DramaForge/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

SQLite 部署建议保持单个 Uvicorn 进程，不要加 `--workers`。如果以后改为多进程或多机器部署，建议把 arq Worker 再拆成独立进程，并使用 PostgreSQL 等服务端数据库。

## 健康检查

后端健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

查看进程：

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*uvicorn*app.main*" } |
  Select-Object ProcessId, CommandLine
```

确认 Redis：

```powershell
redis-cli -u redis://127.0.0.1:6379/0 ping
```

## 常见问题

### 图片任务一直停在 queued

优先检查：

1. 后端日志是否有 `Embedded media generation worker started`。
2. `.env` 中 `REDIS_URL` 是否是原生部署可访问的地址，例如 `redis://127.0.0.1:6379/0`。
3. Redis 是否返回 `PONG`。
4. 后端启动工作目录是否为 `dramaForge_bac`。
5. AI API Key 是否有效，余额和模型权限是否正常。

### 任务提交失败

如果接口返回 `Failed to enqueue media generation job`，说明 FastAPI 无法写入 Redis。检查 Redis 地址、端口、防火墙和密码配置。

### Worker 启动后退出

查看后端日志中的 `Embedded media generation worker stopped unexpectedly`。常见原因是 Redis 不可达、依赖未安装、环境变量错误。

### 生成成功但前端看不到图片

检查后端是否能写入 `storage` 目录，并确认 `/storage` 静态路径可访问。
