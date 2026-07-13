import logging
import time
from collections import defaultdict
from fastapi import FastAPI, Depends, HTTPException, Security, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from decouple import config
from schemas import QuizRequest, QuizResponse, QuestionItem
from llm import generate_quiz_questions


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 限流配置：每 IP 每 60 秒最多 10 次请求
_RATE_WINDOW = 60
_RATE_MAX = 10
_rate_records: dict[str, list[float]] = defaultdict(list)


app = FastAPI(
    title="QuizForge AI Service",
    description="AI 驱动的测验题目生成微服务",
    version="0.1.0"
)

# CORS 配置：允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=config(
        'CORS_ORIGINS',
        default='*',
        cast=lambda v: [s.strip() for s in v.split(',')]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


INTERNAL_IPS = {"127.0.0.1", "::1", "localhost"}


@app.middleware("http")
async def rate_limit_and_monitor(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 内部服务调用（Django→FastAPI）不触发限流
    is_internal = client_ip in INTERNAL_IPS

    if not is_internal:
        _rate_records[client_ip] = [
            t for t in _rate_records[client_ip] if now - t < _RATE_WINDOW
        ]
        if not _rate_records[client_ip]:
            del _rate_records[client_ip]

        if len(_rate_records[client_ip]) >= _RATE_MAX:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")

        _rate_records[client_ip].append(now)

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    logger.info(
        f"IP={client_ip} | {'内部' if is_internal else '外部'} | "
        f"{request.method} {request.url.path} | "
        f"状态={response.status_code} | 耗时={elapsed:.2f}s"
    )
    return response


#  Token 认证配置 
security = HTTPBearer()                                         # 使用 HTTP Bearer Token 认证方式
INTERNAL_TOKEN = config('INTERNAL_TOKEN')                       # 从 .env 读取内部 Token

def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)     # 从请求头中获取 Token
):
    if credentials.credentials != INTERNAL_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="无效的认证令牌，请检查 Authorization 头"
        )
    return credentials.credentials




@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "QuizForge AI Service", "version": "0.1.0"}


router = APIRouter(prefix="/api/v1")


@router.post("/ai/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    req: QuizRequest,
    token: str = Depends(verify_token)
):
    logger.info(f"收到生成请求 → 内容长度: {len(req.content)} 字符, 题目数量: {req.count}")

    try:
        questions_data = await generate_quiz_questions(req.content, req.count)
    except Exception as e:
        logger.error(f"生成题目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 生成失败，请稍后重试")

    questions = [QuestionItem(**q) for q in questions_data]

    return QuizResponse(questions=questions)


app.include_router(router)