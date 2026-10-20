import logging
import time
from fastapi import FastAPI, Depends, HTTPException, Security, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from decouple import config
from schemas import QuizRequest, QuizResponse, QuestionItem, KPRequest, KPResponse, KPItem
from llm import generate_quiz_questions, extract_knowledge_points
from redis_store import rate_limit_ok


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 限流配置：每 IP 每 60 秒最多 10 次请求（计数存 Redis，多副本共享）
_RATE_WINDOW = 60
_RATE_MAX = 10

# 内部服务调用令牌（Django→FastAPI）。带此令牌的请求视为内部调用，不参与限流。
INTERNAL_TOKEN = config('INTERNAL_TOKEN')


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

    # 判断是否内部调用：① 携带正确的内部令牌；② 来自本机回环地址。
    # 注意：不能只看 IP —— 容器里 Django 的源 IP 是内网地址，不是 127.0.0.1；
    # 若只按 IP 判断，内部调用会被限流，导致"每分钟最多 10 次生成"卡死整个后端。
    auth_header = request.headers.get("authorization", "")
    is_internal = (
        auth_header == f"Bearer {INTERNAL_TOKEN}"
        or client_ip in INTERNAL_IPS
    )

    if not is_internal:
        # 滑动窗口限流，计数存 Redis（多副本一致）；Redis 不可用时降级
        if not await rate_limit_ok(f"rl:ai:{client_ip}", _RATE_MAX, _RATE_WINDOW):
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")

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
        questions_data = await generate_quiz_questions(req.content, req.count, req.knowledge_points)
    except Exception as e:
        logger.error(f"生成题目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 生成失败，请稍后重试")

    questions = [QuestionItem(**q) for q in questions_data]

    return QuizResponse(questions=questions)


@router.post("/ai/extract-kp", response_model=KPResponse)
async def extract_kp(
    req: KPRequest,
    token: str = Depends(verify_token)
):
    """从笔记中抽取知识点。"""
    logger.info(f"收到知识点抽取请求 → 内容长度: {len(req.content)} 字符")
    try:
        kps = await extract_knowledge_points(req.content, req.max_points)
    except Exception as e:
        logger.error(f"知识点抽取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="知识点抽取失败，请稍后重试")
    return KPResponse(knowledge_points=[KPItem(**k) for k in kps])


app.include_router(router)
