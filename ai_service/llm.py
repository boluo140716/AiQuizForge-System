import asyncio
import difflib
import hashlib
import json
import logging
import threading
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from decouple import config
from prompt import build_prompt, split_content, build_kp_prompt
from schemas import QuestionItem, QuizOutput, KPOutput
from redis_store import cache_get, cache_set
from quality import filter_by_quality, log_dropped

logger = logging.getLogger(__name__)

USE_MOCK = config('USE_MOCK', default='false').lower() == 'true'
_llm_client = None
_llm_client_lock = threading.Lock()

# 缓存 TTL（秒）：同一篇笔记 + 相同题数在 TTL 内命中，避免重复调用大模型。
# 缓存存 Redis（多副本共享），键形如 llm:cache:{md5}。
_CACHE_TTL = 300

def _cache_key(content: str, count: int, knowledge_points: list[str] | None = None) -> str:
    # 知识点列表也参与缓存键：否则同一笔记带上不同知识点时会命中旧缓存
    kp_part = "|".join(knowledge_points or [])
    return "llm:cache:" + hashlib.md5(f"{content}_{count}_{kp_part}".encode()).hexdigest()

async def _cache_get(content: str, count: int, knowledge_points: list[str] | None = None) -> list[dict] | None:
    raw = await cache_get(_cache_key(content, count, knowledge_points))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("缓存内容解析失败，忽略本次缓存")
        return None
    logger.info(f"缓存命中，直接返回 {len(data)} 道题目")
    return data

async def _cache_set(content: str, count: int, data: list[dict], knowledge_points: list[str] | None = None):
    await cache_set(
        _cache_key(content, count, knowledge_points),
        json.dumps(data, ensure_ascii=False),
        _CACHE_TTL,
    )



def _get_llm_client():
    global _llm_client
    if _llm_client is None:
        with _llm_client_lock:
            if _llm_client is None:
                _llm_client = ChatOpenAI(
                    model=config('LLM_MODEL', default='deepseek-v4-flash'),
                    api_key=config('LLM_API_KEY'),
                    base_url=config('LLM_BASE_URL', default='https://api.deepseek.com'),
                    temperature=0.4,
                    max_completion_tokens=4000,
                    timeout=config('LLM_TIMEOUT', default=60, cast=int),
                )
    return _llm_client


def _generate_mock_questions(content: str, count: int) -> List[Dict]:
    logger.warning("当前使用模拟模式生成题目（USE_MOCK=true）")
    mock_questions = []
    for i in range(1, count + 1):
        mock_questions.append({
            "stem": f"根据笔记内容，第 {i} 道模拟题是什么？",
            "options": [
                "选项一",
                "选项二",
                "选项三",
                "选项四"
            ],
            "answer": "A",
            "explanation": f"这是第 {i} 道模拟题的解析。"
        })
    return mock_questions


async def _generate_from_chunk(content: str, count: int, chunk_index: int, total_chunks: int,
                               knowledge_points: list[str] | None = None) -> List[Dict]:
    """对单个文本块生成题目"""
    prompt_text = build_prompt(content, count, chunk_index, total_chunks, knowledge_points)
    logger.info(f"Chunk {chunk_index+1}/{total_chunks} Prompt 长度: {len(prompt_text)} 字符")

    parser = JsonOutputParser(pydantic_object=QuizOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严格的出题系统，只输出 JSON 对象，不输出任何其他内容。\n\n{format_instructions}"),
        ("human", "{input}")
    ])

    chain = prompt | _get_llm_client().with_config({
        "metadata": {"run_name": "generate_quiz"}
    }) | parser

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    chain.invoke,
                    {
                        "input": prompt_text,
                        "format_instructions": parser.get_format_instructions()
                    }
                ),
                timeout=config('LLM_TIMEOUT', default=60, cast=int) + 30
            )
            questions = result['questions']
            logger.info(f"Chunk {chunk_index+1} 成功生成 {len(questions)} 道题目")

            if len(questions) < count and attempt < max_retries - 1:
                logger.warning(
                    f"Chunk {chunk_index+1} 生成数量不足：期望 {count} 道，实际 {len(questions)} 道，"
                    f"第 {attempt + 1} 次重试..."
                )
                continue

            if len(questions) < count:
                logger.warning(
                    f"Chunk {chunk_index+1} 生成数量不足：期望 {count} 道，实际 {len(questions)} 道，"
                    f"已重试 {max_retries} 次仍不足"
                )
            return questions

        except Exception as e:
            logger.error(f"Chunk {chunk_index+1} 生成失败（第 {attempt + 1}/{max_retries} 次）: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Chunk {chunk_index+1} 在 {max_retries} 次尝试后仍无法生成有效题目。")


def _deduplicate_questions(questions: list[dict], similarity_threshold: float = 0.7) -> list[dict]:
    """题干去重：移除高度相似的题目，使用 SequenceMatcher 计算相似度"""
    if len(questions) <= 1:
        return questions
    result = []
    for q in questions:
        stem = q['stem'].strip()
        is_dup = False
        for existing in result:
            existing_stem = existing['stem'].strip()
            if stem in existing_stem or existing_stem in stem:
                is_dup = True
                break
            # 使用 SequenceMatcher 计算整体相似度（比单纯字符集重叠更准确）
            matcher = difflib.SequenceMatcher(None, stem, existing_stem)
            ratio = matcher.ratio()
            if ratio >= similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            result.append(q)
    if len(result) < len(questions):
        logger.info(f"去重：{len(questions)} → {len(result)} 道题目")
    return result


async def extract_knowledge_points(content: str, max_points: int = 8) -> List[Dict]:
    """从笔记中抽取知识点，返回 [{"name":..., "description":...}]。"""
    if USE_MOCK:
        return [{"name": "示例知识点", "description": "模拟模式生成的知识点"}]

    parser = JsonOutputParser(pydantic_object=KPOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个只输出 JSON 的知识点抽取助手。\n\n{format_instructions}"),
        ("human", "{input}")
    ])
    chain = prompt | _get_llm_client().with_config({
        "metadata": {"run_name": "extract_kp"}
    }) | parser

    prompt_text = build_kp_prompt(content, max_points)
    result = await asyncio.wait_for(
        asyncio.to_thread(
            chain.invoke,
            {
                "input": prompt_text,
                "format_instructions": parser.get_format_instructions()
            }
        ),
        timeout=config('LLM_TIMEOUT', default=60, cast=int) + 30
    )
    return result.get('knowledge_points', [])


async def generate_quiz_questions(content: str, count: int,
                                  knowledge_points: list[str] | None = None) -> List[Dict]:
    if USE_MOCK:
        return _generate_mock_questions(content, count)

    cached = await _cache_get(content, count, knowledge_points)
    if cached is not None:
        return cached

    chunks = split_content(content)

    if len(chunks) == 1:
        result = await _generate_from_chunk(chunks[0], count, 0, 1, knowledge_points)
        result, dropped = filter_by_quality(result)
        log_dropped(dropped, logger)
        if result:
            await _cache_set(content, count, result, knowledge_points)
        return result

    logger.info(f"笔记过长（{len(content)} 字符），已切分为 {len(chunks)} 块，使用 Map-Reduce 模式生成")

    questions_per_chunk = count // len(chunks)
    remainder = count % len(chunks)

    tasks = []
    for i, chunk in enumerate(chunks):
        chunk_count = questions_per_chunk + (1 if i < remainder else 0)
        if chunk_count == 0:
            continue
        tasks.append(_generate_from_chunk(chunk, chunk_count, i, len(chunks), knowledge_points))

    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_questions = []
    failed_chunks = 0
    for i, result_chunk in enumerate(chunk_results):
        if isinstance(result_chunk, Exception):
            logger.error(f"Chunk {i} 生成失败（已跳过，不影响其他块）: {result_chunk}")
            failed_chunks += 1
            continue
        all_questions.extend(result_chunk)

    if failed_chunks > 0:
        logger.warning(f"Map-Reduce: {failed_chunks}/{len(chunks)} 个块失败，已跳过")

    all_questions = _deduplicate_questions(all_questions)
    all_questions, dropped = filter_by_quality(all_questions)
    log_dropped(dropped, logger)
    result = all_questions[:count]
    if result:
        await _cache_set(content, count, result, knowledge_points)
    logger.info(f"Map-Reduce 完成，共生成 {len(result)} 道题目（{len(chunks)} 块并发）")
    return result
