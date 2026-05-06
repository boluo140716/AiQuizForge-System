import logging
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from decouple import config
from schemas import QuizRequest, QuizResponse, QuestionItem
from llm import generate_quiz_questions


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



app = FastAPI(
    title="QuizForge AI Service",
    description="AI 驱动的测验题目生成微服务",
    version="0.1.0"
)


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




@app.post("/ai/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    req: QuizRequest,                                           
    token: str = Depends(verify_token)                          
):
    logger.info(f"收到生成请求 → 内容长度: {len(req.content)} 字符, 题目数量: {req.count}")

    try:
        questions_data = generate_quiz_questions(req.content, req.count)
    except Exception as e:
        logger.error(f"生成题目失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")

    questions = [QuestionItem(**q) for q in questions_data]

    return QuizResponse(questions=questions)


