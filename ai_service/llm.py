
import json
import logging
from typing import List, Dict
from openai import OpenAI
from decouple import config
from prompt import build_prompt

# 配置日志
logger = logging.getLogger(__name__)

# 是否使用模拟模式
USE_MOCK = config('USE_MOCK', default='false').lower() == 'true'


def _call_llm(prompt: str) -> str:   # 调用大模型
    client = OpenAI(
        api_key=config('LLM_API_KEY'),
        base_url=config('LLM_BASE_URL', default='https://api.openai.com/v1')
    )
    response = client.chat.completions.create(
        model=config('LLM_MODEL', default='qwen3.6-plus'),
        messages=[
            {
                "role": "system",
                "content": "你是一个严格的出题系统，只输出 JSON 数组，不输出任何其他内容。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,        # 控制创造性，0.7 比较平衡
        max_tokens=2000         # 最大输出长度
    )
    # 提取模型返回的文本内容
    return response.choices[0].message.content.strip()


def _generate_mock_questions(content: str, count: int) -> List[Dict]:   # 模拟模式
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
            "explanation": f"这是第 {i} 道模拟题的解析。实际部署时，这里会是大模型生成的智能解析。"
        })
    return mock_questions


def generate_quiz_questions(content: str, count: int) -> List[Dict]:   # 生成测验题目
    if USE_MOCK:
        return _generate_mock_questions(content, count)

    
    prompt = build_prompt(content, count)
    logger.info(f"生成的 Prompt 长度: {len(prompt)} 字符")

    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 调用大模型获取原始输出
            raw_output = _call_llm(prompt)
            logger.info(f"大模型原始输出（前200字符）: {raw_output[:200]}...")

            # 尝试解析为 JSON 列表
            questions = json.loads(raw_output)

            # 确保解析结果是列表
            if not isinstance(questions, list):
                raise ValueError("大模型返回的不是 JSON 数组")

            # 确保题目数量符合要求
            if len(questions) < count:
                logger.warning(
                    f"大模型只生成了 {len(questions)} 道题，期望 {count} 道"
                )

            logger.info(f"成功生成 {len(questions)} 道题目")
            return questions[:count]  # 只返回需要的数量

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"解析大模型输出失败（第 {attempt + 1}/{max_retries} 次）: {e}")
            if attempt < max_retries - 1:
                prompt = build_prompt(content, count) + \
                    "\n\n【重要】请严格输出纯 JSON 数组，不要包含 markdown 代码块标记，不要有任何额外解释文字。"
            else:
                raise RuntimeError(
                    f"大模型在 {max_retries} 次尝试后仍无法生成有效的 JSON 格式题目。"
                    f"最后一次输出: {raw_output[:300]}"
                )