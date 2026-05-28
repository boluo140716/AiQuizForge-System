import json
import logging
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RetryPolicy
from pydantic import BaseModel, Field
from decouple import config
from prompt import build_prompt

logger = logging.getLogger(__name__)

USE_MOCK = config('USE_MOCK', default='false').lower() == 'true'


class Question(BaseModel):
    stem: str = Field(description="题目题干")
    options: List[str] = Field(description="选项列表")
    answer: str = Field(description="正确答案")
    explanation: str = Field(description="解析")


def _get_llm_client():
    return ChatOpenAI(
        model=config('LLM_MODEL', default='deepseek-v4-flash'),
        api_key=config('LLM_API_KEY'),
        base_url=config('LLM_BASE_URL', default='https://api.deepseek.com'),
        temperature=0.7,
        max_completion_tokens=2000,
    )


def _generate_mock_questions(content: str, count: int) -> List[Dict]:
    logger.warning("当前使用模拟模式生成题目（USE_MOCK=true）")
    mock_questions = []
    for i in range(1, count + 1):
        mock_questions.append({
            "stem": f"根据笔记内容，第 {i} 道模拟题是什么？",
            "options": [
                "A: 选项一",
                "B: 选项二",
                "C: 选项三",
                "D: 选项四"
            ],
            "answer": "A",
            "explanation": f"这是第 {i} 道模拟题的解析。"
        })
    return mock_questions


def generate_quiz_questions(content: str, count: int) -> List[Dict]:
    if USE_MOCK:
        return _generate_mock_questions(content, count)

    prompt_text = build_prompt(content, count)
    logger.info(f"生成的 Prompt 长度: {len(prompt_text)} 字符")

    parser = JsonOutputParser(pydantic_object=Question)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严格的出题系统，只输出 JSON 数组，不输出任何其他内容。\n\n{format_instructions}"),
        ("human", "{input}")
    ])

    chain = prompt | _get_llm_client().with_config({
        "metadata": {"run_name": "generate_quiz"}
    }) | parser

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = chain.invoke({
                "input": prompt_text,
                "format_instructions": parser.get_format_instructions()
            })
            logger.info(f"成功生成 {len(result)} 道题目")
            return result[:count]

        except Exception as e:
            logger.error(f"生成题目失败（第 {attempt + 1}/{max_retries} 次）: {e}")
            if attempt < max_retries - 1:
                continue
            else:
                raise RuntimeError(f"在 {max_retries} 次尝试后仍无法生成有效题目。错误: {e}")
