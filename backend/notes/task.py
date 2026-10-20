import logging
import json
import random
import traceback
from datetime import timedelta
import httpx
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from notes.models import (
    Quiz, Question, FailedTask, KnowledgePoint, QuestionKnowledgePoint,
)
from notes.progress import publish_progress

logger = logging.getLogger(__name__)


def _touch_heartbeat(quiz_id: int) -> None:
    """更新任务心跳时间，供「看门狗」判断任务是否卡死。"""
    Quiz.objects.filter(id=quiz_id).update(heartbeat_at=timezone.now())


def _set_progress(quiz, stage: str, done: int, total: int, message: str = '') -> None:
    """保存进度到数据库，并广播给 SSE。"""
    payload = {'stage': stage, 'done': done, 'total': total, 'message': message}
    try:
        Quiz.objects.filter(id=quiz.id).update(progress=payload)
    except Exception as e:
        logger.warning("写入进度失败 quiz=%s: %s", quiz.id, e)
    publish_progress(quiz.id, payload)


def _retry_countdown(retries: int) -> int:
    """指数退避 + 随机抖动：60s、120s、240s，各自再加 0~30s 随机。

    退避：越失败等得越久，给下游恢复时间。
    抖动：把同时失败的任务打散，避免它们在同一秒集体重试（惊群）。
    """
    return 60 * (2 ** retries) + random.randint(0, 30)


def _fail_quiz(quiz, message, *, exc=None, task_id=None, retries=0):
    """把测验标记为失败，并把这次失败写入 DLQ（failed_task 表）留档。"""
    quiz.status = 'failed'
    quiz.error_message = message
    quiz.save(update_fields=['status', 'error_message'])
    _set_progress(quiz, 'failed', 0, 1, message)

    try:
        FailedTask.objects.create(
            task_name='notes.task.generate_quiz',
            task_id=task_id,
            args=[quiz.id],
            kwargs={},
            error=str(exc) if exc else message,
            traceback=traceback.format_exc() if exc else '',
            retries=retries,
            status='pending',
        )
    except Exception as record_err:  # 记录失败不能掩盖原始失败
        logger.error("写入失败任务记录失败: %s", record_err)


def _call_ai_service_sync(url: str, payload: dict, headers: dict) -> dict:
    """同步调用 AI 服务，避免 Celery Worker 内的事件循环冲突"""
    with httpx.Client(timeout=httpx.Timeout(10.0, read=120.0)) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

@shared_task(bind=True,max_retries=3)
def generate_quiz(self, quiz_id:int, trace_id:str=''):
    try:
        quiz=Quiz.objects.select_related('note').get(id=quiz_id)
    except Quiz.DoesNotExist:
        logger.error(f"Quiz with id {quiz_id} 不存在")
        return
    
    if quiz.status != 'processing':
        logger.warning(f'Quiz {quiz_id} 状态为{quiz.status}，无需重新生成')
        return
    note=quiz.note
    if not note or not note.content_plain or len(note.content_plain)<20:
        _fail_quiz(quiz, '笔记内容过短')
        return

    # 记录心跳：任务开始处理（看门狗据此判断任务是否卡死）
    _touch_heartbeat(quiz.id)

    # 先抽取知识点（失败不影响出题；已有知识点则跳过）
    _set_progress(quiz, 'analyzing', 0, 1, '正在抽取知识点')
    try:
        from notes.kp import extract_and_store_kps
        kp_count = extract_and_store_kps(note, trace_id)
        if kp_count:
            logger.info("已为笔记 %s 抽取 %s 个知识点", note.id, kp_count)
    except Exception as e:
        logger.warning("知识点抽取失败（不影响出题）: %s", e)

    _set_progress(quiz, 'generating', 0, 1, '正在调用 AI 服务')

    # 准备调用 FastAPI
    ai_service_url = settings.AI_SERVICE_URL + '/api/v1/ai/generate-quiz'
    # 准备请求头
    headers = {
        'Authorization': f'Bearer {settings.AI_SERVICE_TOKEN}',
        'Content-Type': 'application/json',
        'X-Trace-Id': trace_id,
    }
    # 准备请求体（带上知识点，便于模型给每道题标注 kp）
    kp_names = list(
        KnowledgePoint.objects.filter(note_links__note=note).values_list('name', flat=True)
    )
    payload = {
        'content': note.content_plain,
        'count': quiz.question_count,
        'knowledge_points': kp_names,
    }
    try:
        data = _call_ai_service_sync(ai_service_url, payload, headers)
    except httpx.ConnectError as e:
        logger.error(f"无法连接到AI服务，请确认FastAPI已启动: {e}")
        try:
            self.retry(exc=e, countdown=_retry_countdown(self.request.retries))
        except self.MaxRetriesExceededError:
            _fail_quiz(quiz, 'AI服务连接失败，请检查服务是否运行',
                       exc=e, task_id=self.request.id, retries=self.request.retries)
            return
    except httpx.ReadTimeout as e:
        logger.error(f"AI服务响应超时: {e}")
        try:
            self.retry(exc=e, countdown=_retry_countdown(self.request.retries))
        except self.MaxRetriesExceededError:
            _fail_quiz(quiz, 'AI服务响应超时，请稍后重试',
                       exc=e, task_id=self.request.id, retries=self.request.retries)
            return
    except httpx.HTTPStatusError as e:
        # FastAPI 内部已重试过，HTTP 错误视为最终失败，不再重试
        detail = '未知错误'
        try:
            detail = e.response.json().get('detail', e.response.text)
        except Exception:
            detail = e.response.text or f'HTTP {e.response.status_code}'
        logger.error(f"AI服务返回错误 {e.response.status_code}: {detail}")
        _fail_quiz(quiz, f'AI 生成失败：{detail}',
                   exc=e, task_id=self.request.id, retries=self.request.retries)
        return
    except Exception as e:
        logger.error(f"调用AI服务未知异常: {str(e)}")
        try:
            self.retry(exc=e, countdown=_retry_countdown(self.request.retries))
        except self.MaxRetriesExceededError:
            _fail_quiz(quiz, f'生成失败：{str(e)}',
                       exc=e, task_id=self.request.id, retries=self.request.retries)
            return
    
    questions_data=data.get('questions',[])
    if not questions_data:
        _fail_quiz(quiz, 'ai服务返回空数据',
                   task_id=self.request.id, retries=self.request.retries)
        return

    _set_progress(quiz, 'saving', 1, 1, '正在保存题目')
    kp_map = {kp.name: kp for kp in KnowledgePoint.objects.filter(note_links__note=note)}
    unmatched_kp = 0
    for q_data in questions_data:
        question = Question.objects.create(
            quiz=quiz,
            stem=q_data['stem'],
            options=q_data['options'],
            answer=q_data.get('answer',''),
            explanation=q_data.get('explanation',''),
        )
        kp_name = (q_data.get('kp') or '').strip()
        kp = kp_map.get(kp_name)
        if kp is not None:
            QuestionKnowledgePoint.objects.get_or_create(question=question, kp=kp)
        elif kp_name:
            unmatched_kp += 1

    if unmatched_kp:
        logger.warning("有 %s 道题的知识点未能匹配到题库", unmatched_kp)

    quiz.status='completed'
    quiz.heartbeat_at = timezone.now()
    quiz.save()
    _set_progress(quiz, 'done', 1, 1, '生成完成')
    logger.info(f'Quiz {quiz_id} 生成完成,共{len(questions_data)}题')


# ===== 看门狗：回收卡死的生成任务 =====
@shared_task
def reap_stuck_quizzes():
    """定期扫描：状态仍是 processing、但心跳早已过期的任务，判定为卡死并标记失败。

    这是最后一道「对账」机制：无论任务因为什么原因没有收尾，
    都不能让一条测验永远停在「生成中」。
    """
    # 防多实例并发执行（存在多个 beat 时，同一时刻只让一个跑）
    if not cache.add('watchdog:reap_stuck_quizzes', '1', timeout=120):
        return 0

    threshold = timezone.now() - timedelta(minutes=settings.QUIZ_STUCK_MINUTES)
    stuck = Quiz.objects.filter(status='processing').filter(
        Q(heartbeat_at__lt=threshold)
        | Q(heartbeat_at__isnull=True, created_at__lt=threshold)
    )
    count = stuck.update(
        status='failed',
        error_message='任务超时或丢失，已由看门狗自动回收',
    )
    if count:
        logger.warning('看门狗回收了 %s 个卡死任务', count)
    return count
