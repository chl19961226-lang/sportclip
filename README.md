# SportClip · 多合一运动视频剪辑

一个端到端的原型：上传一段（或多段）运动视频，自动识别运动种类、检出高光时刻、剪辑拼接成片，并根据所选关键字生成分享文案。

## 架构

```
┌──────────────┐    REST/JSON    ┌────────────────────────────────────┐
│  Next.js 前端 │ ───────────────▶│           FastAPI 后端              │
│  上传/关键字  │ ◀───────────────│  任务编排 + 进度回调                │
└──────────────┘                  └─────────────────┬──────────────────┘
                                                    │
                          ┌─────────────────────────┼─────────────────────────┐
                          ▼                         ▼                         ▼
                ┌──────────────────┐     ┌──────────────────┐       ┌──────────────────┐
                │  YOLO 主体检测    │     │  VLM 高光检测     │       │  LLM 文案生成     │
                │ (ultralytics)    │     │ (OpenAI/可 mock)  │       │ (OpenAI/可 mock)  │
                └────────┬─────────┘     └────────┬─────────┘       └────────┬─────────┘
                         │                        │                          │
                         ▼                        ▼                          ▼
                关键帧 + 运动分类         高光时间区间             分享文案 + Hashtag
                                         ↓
                                    ffmpeg 剪辑拼接 → 输出 highlight.mp4
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, ultralytics (YOLOv8), OpenCV, ffmpeg, OpenAI SDK（可选）
- **前端**: Next.js 14 (App Router) + TypeScript + TailwindCSS + lucide-react
- **依赖**: 系统安装 `ffmpeg`

## 目录

```
windsurf-project/
├── backend/        # FastAPI 服务
├── frontend/       # Next.js 前端
├── start.sh        # 一键启动脚本（mac/linux）
└── README.md
```

## 快速开始

### 1. 安装系统依赖

```bash
brew install ffmpeg          # mac
# or: sudo apt install ffmpeg
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # 可选：填入 OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

首次启动会自动下载 `yolov8n.pt`（约 6MB）。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

### 4. 一键启动

```bash
./start.sh
```

## 工作模式

后端按以下顺序降级：

| 模块 | 优选 | 降级 |
|------|------|------|
| 主体检测 | YOLOv8 (本地) | 等距均匀采样 |
| 运动分类 | VLM 关键帧识别 | YOLO 启发式（COCO 类别 → 运动类型） |
| 高光检测 | VLM 评分关键帧 | 运动检测幅度（光流/帧差） |
| 文案生成 | LLM (OpenAI) | 模板拼接 |

> 没有 `OPENAI_API_KEY` 时整个流程仍可跑通，结果由本地启发式生成。

## API

| Method | Path | 描述 |
|--------|------|------|
| POST | `/api/jobs` | 上传视频，创建任务（multipart: `file`, `keywords[]`, `style`） |
| GET | `/api/jobs/{id}` | 查询任务状态、进度、结果 |
| GET | `/api/files/{id}/highlight` | 下载剪辑后的高光视频 |
| GET | `/api/files/{id}/thumbnail` | 下载封面缩略图 |

## 注意

这是原型代码，重在跑通主流程。生产化需要替换：

- 任务存储：内存 → Redis / DB
- 文件存储：本地 → 对象存储
- 任务执行：后台线程 → Celery / RQ
- 模型：YOLOv8n + 启发式 → 自训练运动分类器 + 关键动作检测器
