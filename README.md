# AiQuizForge

AI 驱动的笔记管理与测验生成平台。用户可以创建笔记本，使用 Markdown 编写笔记，并通过 AI 自动生成选择题测验。支持错题本管理，帮助巩固学习成果。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 API | Django 4.2 + Django REST Framework 3.14 |
| 异步任务 | Celery 5.3 + Redis |
| 数据库 | MySQL |
| 前端 | Vue 3.5 + Vite 8 + Element Plus 2.13 |
| 状态管理 | Pinia 3.0 |
| AI 服务 | FastAPI + OpenAI SDK（对接阿里云 DashScope Qwen 模型） |
| 认证 | SimpleJWT（JWT 双 Token 机制） |

## 项目结构

```
AiQuizForge-System/
├── backend/                    # Django REST API (端口 8000)
│   ├── config/                 # Django 配置：settings、URL 路由、Celery、限流
│   ├── notes/                  # 核心业务：笔记、测验、题目、答题记录、错题本
│   │   ├── task.py             # Celery 异步任务（调用 AI 服务生成题目）
│   │   └── tests/              # 单元测试
│   └── users/                  # 用户模型（自定义 User）、注册登录
├── frontend/                   # Vue 3 前端 (端口 3000)
│   └── src/
│       ├── api/index.js        # 所有后端 API 封装
│       ├── views/              # 页面组件
│       ├── stores/             # Pinia 状态管理
│       └── router/             # 路由配置 + 导航守卫
└── ai_service/                 # FastAPI AI 微服务 (端口 8001)
    ├── main.py                 # API 入口 + 认证
    ├── llm.py                  # LLM 调用封装（含重试逻辑 + Mock 模式）
    ├── prompt.py               # Prompt 模板构建
    └── schemas.py              # Pydantic 数据模型
```

## 功能概览

- **笔记本管理**：创建、编辑、删除笔记本，按笔记本组织笔记
- **Markdown 笔记**：支持 Markdown 编辑器（Toast UI Editor）编写和编辑笔记，自动提取纯文本
- **AI 测验生成**：基于笔记内容，通过 AI 自动生成 1-10 道选择题，支持异步生成与状态轮询
- **在线答题**：逐题作答，提交后自动评分，生成详细答题报告
- **错题本**：自动收录错题，支持按笔记本/测验/标签筛选，支持重做错题
- **用户中心**：自定义头像、昵称，查看个人统计数据（笔记数、测验数、平均正确率）

## 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 6.0+

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd AiQuizForge-System
```

### 2. 配置并启动后端

```bash
cd backend

# 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量（复制并编辑 .env）
# 需要填写：SECRET_KEY、数据库密码、Redis 密码、AI 服务 Token

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 启动 Django 开发服务器
python manage.py runserver
```

### 3. 启动 Celery Worker（必须，否则测验生成无法执行）

```bash
# 在 backend/ 目录下，确保 Redis 已启动
celery -A config worker -l info
```

### 4. 配置并启动 AI 服务

```bash
cd ai_service

# 安装依赖
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env（LLM_API_KEY、LLM_BASE_URL、LLM_MODEL、INTERNAL_TOKEN）
# INTERNAL_TOKEN 需与后端 AI_SERVICE_TOKEN 一致

# 启动
python -m uvicorn main:app --reload --port 8001
```

> 开发时可设置 `USE_MOCK=true` 跳过 LLM 调用，返回模拟题目。

### 5. 启动前端

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:3000

## 环境变量

### 后端 (`backend/.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | — | Django 密钥（必填） |
| `DB_NAME` | `quizforge_db` | 数据库名称 |
| `DB_USER` | `root` | 数据库用户 |
| `DB_PASSWORD` | — | 数据库密码 |
| `DB_HOST` | `127.0.0.1` | 数据库地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `REDIS_HOST` | `127.0.0.1` | Redis 地址（Celery 用 DB 0，缓存用 DB 1） |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | — | Redis 密码 |
| `AI_SERVICE_URL` | `http://127.0.0.1:8001` | AI 服务地址 |
| `AI_SERVICE_TOKEN` | `quizforge-internal-secret-token-2026` | AI 服务通信令牌（需与 AI 服务 `INTERNAL_TOKEN` 一致） |

### AI 服务 (`ai_service/.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | — | LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容 API 地址 |
| `LLM_MODEL` | `qwen3.6-plus` | 模型名称 |
| `USE_MOCK` | `false` | 设为 `true` 跳过 LLM，返回模拟数据 |
| `INTERNAL_TOKEN` | — | 内部通信令牌（需与后端 `AI_SERVICE_TOKEN` 一致） |

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register/` | 注册 |
| POST | `/api/v1/auth/login/` | 登录（返回 access + refresh token） |
| POST | `/api/v1/auth/token/refresh/` | 刷新 Token |
| GET | `/api/v1/auth/me/` | 获取当前用户信息 |
| PATCH | `/api/v1/auth/me/` | 更新用户信息 |
| GET | `/api/v1/auth/profile/` | 获取用户统计数据 |

### 笔记本

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/notebooks/` | 笔记本列表 |
| POST | `/api/v1/notebooks/` | 创建笔记本 |
| GET | `/api/v1/notebooks/{id}/` | 笔记本详情 |
| PUT/PATCH | `/api/v1/notebooks/{id}/` | 更新笔记本 |
| DELETE | `/api/v1/notebooks/{id}/` | 删除笔记本 |

### 笔记

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/notes/` | 笔记列表（支持搜索、笔记本筛选、标签筛选、分页） |
| POST | `/api/v1/notes/` | 创建笔记（自动提取纯文本） |
| GET | `/api/v1/notes/{id}/` | 笔记详情 |
| PUT/PATCH | `/api/v1/notes/{id}/` | 更新笔记 |
| DELETE | `/api/v1/notes/{id}/` | 删除笔记 |

### 测验

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/quizzes/` | 测验历史列表 |
| POST | `/api/v1/quizzes/generate/{note_id}/` | 生成测验（异步，限流 5次/分钟） |
| GET | `/api/v1/quizzes/{id}/status/` | 查询生成状态（前端轮询此接口） |
| POST | `/api/v1/quizzes/{id}/cancel-delete/` | 取消正在生成的测验 |
| POST | `/api/v1/quizzes/{id}/delete/` | 删除测验 |
| GET | `/api/v1/quizzes/{id}/questions/` | 获取测验题目（不含答案） |
| POST | `/api/v1/quizzes/{id}/attempt/` | 提交答案 |
| GET | `/api/v1/quizzes/{id}/attempts/` | 答题记录 |
| GET | `/api/v1/quizzes/{id}/review/` | 测验复盘（含答案和解析） |

### 错题本

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/wrong-questions/list/` | 错题列表（支持分页、筛选） |
| GET | `/api/v1/wrong-questions/tags/` | 所有标签 |
| POST | `/api/v1/wrong-questions/re-practice/` | 重做错题 |
| DELETE | `/api/v1/wrong-questions/{id}/remove/` | 移除错题 |

## 运行测试

```bash
cd backend

# 全部测试
python manage.py test

# 指定模块
python manage.py test notes.tests.test_quiz

# 指定用例
python manage.py test notes.tests.test_quiz.QuizGenerateTest.test_generate_quiz_success
```

## 测验生成流程

```
前端点击"生成测验"
  → POST /api/v1/quizzes/generate/{note_id}/
  → 后端创建 Quiz(status=processing) → Celery 异步任务入队
  → Celery Worker 调用 AI 服务 POST /ai/generate-quiz
  → AI 服务调用 LLM（最多重试 3 次）→ 返回题目 JSON
  → Celery Worker 保存题目 → 更新 Quiz(status=completed)
  → 前端每 2 秒轮询 status 接口 → 状态变为 completed 后拉取题目
```

## 前端页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | 笔记本侧边栏 + 仪表盘 |
| `/login` | 登录 | |
| `/register` | 注册 | |
| `/notes` | 笔记列表 | 搜索、筛选、分页 |
| `/notes/new` | 新建笔记 | Markdown 编辑器 |
| `/notes/:id/edit` | 编辑笔记 | |
| `/quiz/:id` | 答题页 | 逐题作答、自动评分 |
| `/quiz/:id/review` | 测验复盘 | 答案解析、答题历史 |
| `/quiz-history` | 测验历史 | 统计卡片 + 测验列表 |
| `/wrong-questions` | 错题本 | 筛选、移除、重做 |
| `/profile` | 个人中心 | 头像、昵称、统计数据 |
