# AiQuizForge

AI 驱动的笔记管理与测验生成平台。用户创建笔记本，使用 Markdown 编写笔记，通过 AI大模型自动生成选择题测验。支持在线答题、错题本管理和个人学习统计，旨在协助用户更高效的进行学习和记忆。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 API | Django 4.2 + Django REST Framework 3.14 |
| 异步任务 | Celery 5.3 + Redis |
| 数据库 | MySQL 8.0 |
| 前端 | Vue 3.5 + Vite 8 + Element Plus 2.13 |
| 状态管理 | Pinia 3.0 |
| AI 服务 | FastAPI +langchain+OpenAI SDK（对接deepseek模型） |
| 认证 | SimpleJWT（JWT 双 Token 机制） |
| 容器化 | Docker + Docker Compose |

## 项目页面
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/820f3c60-365e-4a74-a5e2-89b599081beb" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/29c974ce-1df6-4ca4-9f31-b07281aa085a" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/a9222bf9-70b9-4999-ae68-5a3229645d00" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/bf5a5e63-4f6f-488d-add9-6587a0f6ade5" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/d1d18fcc-4184-4e2a-9483-a2f1effb9e02" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/6e8e8067-5baa-417d-b36f-2b2c7935ff51" />
<img width="130" height="110" alt="image" src="https://github.com/user-attachments/assets/0d0faefe-e5b9-461f-9d8e-2a1ae1ac4083" />

## 项目结构

```
AiQuizForge-System/
├── docker-compose.yml            # 一键编排 6 个服务
├── backend/                      # Django REST API（端口 8000）
│   ├── Dockerfile
│   ├── entrypoint.sh             # 容器入口：等待 MySQL/Redis + 自动迁移
│   ├── config/                   # Django 配置：settings、URL、Celery、限流
│   ├── notes/                    # 核心业务：笔记、测验、题目、答题记录、错题本
│   │   ├── task.py               # Celery 异步任务（调用 AI 服务生成题目）
│   │   └── tests/                # 单元测试
│   └── users/                    # 自定义用户模型、认证、个人中心
├── frontend/                     # Vue 3 前端（端口 3000）
│   ├── Dockerfile                # 多阶段构建：Node 构建 + Nginx 提供
│   ├── nginx.conf                # Nginx 反向代理配置
│   └── src/
│       ├── api/index.js          # 所有后端 API 封装
│       ├── views/                # 11 个页面组件
│       ├── stores/               # Pinia 状态管理
│       └── router/               # 路由配置 + 导航守卫
└── ai_service/                   # FastAPI AI 微服务（端口 8001）
    ├── Dockerfile
    ├── main.py                   # API 入口 + Bearer 认证
    ├── llm.py                    # LLM 调用封装（3 次重试 + Mock 模式）
    ├── prompt.py                 # Prompt 模板构建
    └── schemas.py                # Pydantic 数据模型
```

## 功能

- **笔记本管理**：创建、编辑、删除笔记本，按笔记本组织笔记
- **Markdown 笔记**：Toast UI Editor 编辑器，自动提取纯文本供 AI 使用
- **AI 测验生成**：基于笔记内容异步生成 1-10 道选择题，支持状态轮询
- **在线答题**：逐题作答、自动评分、详细答题报告
- **错题本**：自动收录错题，支持按笔记本/测验/标签筛选和重做
- **个人中心**：自定义头像和昵称，查看笔记数、测验数、平均正确率等统计数据

## 快速开始（Docker，推荐）

### 环境要求

- [Docker](https://www.docker.com/products/docker-desktop/) + Docker Compose V2

### 启动
```bash
# 1. 克隆项目到本地（替换为你的真实仓库地址）
git clone https://github.com/boluo140716/AiQuizForge-System.git

# 2. 进入项目目录
cd AiQuizForge-System

# 3. 启动所有服务（首次启动会自动构建镜像，约 3-5 分钟）
docker compose up -d

# 查看启动日志
docker compose logs -f

# 查看各服务状态
docker compose ps
```

访问 **http://localhost:3000** 即可使用。

### 配置 LLM API Key

启动时通过环境变量传入，或创建 `.env` 文件：

```bash
# 方式一：命令行传入
LLM_API_KEY=sk-your-key docker compose up -d

# 方式二：创建 .env 文件（已在 .gitignore 中忽略）
echo 'LLM_API_KEY=sk-your-key' > .env
docker compose up -d
```

> 开发测试时可设 `USE_MOCK=true` 跳过 LLM 调用，返回模拟题目。

### Docker 服务一览

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| `db` | `quizforge-db` | 3306 | MySQL 8.0，自动创建数据库 |
| `redis` | `quizforge-redis` | 6379 | Redis 7，AOF 持久化 |
| `backend` | `quizforge-backend` | 8000 | Django API，启动时自动执行 migrate |
| `celery-worker` | `quizforge-celery` | — | Celery 异步任务（测验生成） |
| `ai-service` | `quizforge-ai` | 8001 | FastAPI AI 微服务 |
| `frontend` | `quizforge-frontend` | 3000 | Nginx 提供 Vue SPA + 反向代理 |

### 常用命令

```bash
# 重建并重启某个服务（代码/配置变更后）
docker compose up -d --build backend
docker compose up -d --build frontend
docker compose up -d --build ai-service

# 停止所有服务
docker compose down

# 停止并清理数据（数据库、Redis、上传文件全部清除）
docker compose down -v

# 查看某个服务的日志
docker compose logs -f backend
docker compose logs -f celery-worker

# 进入容器调试
docker compose exec backend python manage.py shell
docker compose exec db mysql -uroot -proot quizforge_db
```

### 运行测试

```bash
docker compose exec backend python manage.py test
docker compose exec backend python manage.py test notes.tests.test_quiz
```

---

## 传统手动部署（不使用 Docker）

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 6.0+

### 1. 配置并启动后端

```bash
cd backend

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env（参考下方环境变量表）
# 需要填写：SECRET_KEY、DB_PASSWORD、REDIS_PASSWORD、AI_SERVICE_TOKEN

python manage.py migrate
python manage.py runserver
```

### 2. 启动 Celery Worker

```bash
celery -A config worker -l info
```

### 3. 启动 AI 服务

```bash
cd ai_service

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置 .env（LLM_API_KEY、INTERNAL_TOKEN 等）

python -m uvicorn main:app --reload --port 8001
```

### 4. 启动前端

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:3000
