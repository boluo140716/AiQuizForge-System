import logging
import time
from collections import defaultdict
from fastapi import FastAPI, Depends, HTTPException, Security, Request
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


@app.middleware("http")
async def rate_limit_and_monitor(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    _rate_records[client_ip] = [
        t for t in _rate_records[client_ip] if now - t < _RATE_WINDOW
    ]

    if len(_rate_records[client_ip]) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")

    _rate_records[client_ip].append(now)

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    logger.info(
        f"IP={client_ip} | {request.method} {request.url.path} | "
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


@app.post("/ai/generate-quiz", response_model=QuizResponse)
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