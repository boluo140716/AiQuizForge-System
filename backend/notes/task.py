import logging
import json
from celery import shared_task
from django.conf import settings
import httpx
from notes.models import Quiz, Question

logger = logging.getLogger(__name__)


@shared_task(bind=True,max_retries=3)
def generate_quiz(self, quiz_id:int):
    try:
        quiz=Quiz.objects.select_related('note').get(id=quiz_id)
    except Quiz.DoesNotExist:
        logger.error(f"Quiz with id {quiz_id} 不存在")
        return
    
    if quiz.status != 'processing':
        logger.warning(f'Quiz {quiz_id} 状态为{quiz.status}，无需重新生成')
        return
    note=quiz.note
    if not note.content_plain or len(note.content_plain)<20:
        quiz.status='failed'
        quiz.error_message='笔记内容过短'
        quiz.save()
        return
    
    # 准备调用 FastAPI
    ai_service_url = settings.AI_SERVICE_URL + '/ai/generate-quiz'
    # 准备请求头
    headers = {
        'Authorization': f'Bearer {settings.AI_SERVICE_TOKEN}',
        'Content-Type': 'application/json',
    }
    # 准备请求体
    payload = {
        'content': note.content_plain,
        'count': quiz.question_count
    }
    try:
    # 增加超时时间到 120 秒，并分开设置连接超时和读取超时
        with httpx.Client(timeout=httpx.Timeout(10.0, read=120.0)) as client:
            response = client.post(ai_service_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as e:
        logger.error(f"无法连接到AI服务，请确认FastAPI已启动: {e}")
        quiz.status = 'failed'
        quiz.error_message = 'AI服务连接失败，请检查服务是否运行'
        quiz.save()
        return
    except httpx.ReadTimeout as e:
        logger.error(f"AI服务响应超时: {e}")
        quiz.status = 'failed'
        quiz.error_message = 'AI服务响应超时，请稍后重试'
        quiz.save()
        return
    except httpx.HTTPStatusError as e:
        logger.error(f"AI服务返回错误 {e.response.status_code}: {e.response.text}")
        quiz.status = 'failed'
        quiz.error_message = f'AI 服务调用失败：{e.response.status_code}'
        quiz.save()
        return
    except Exception as e:
        logger.error(f"调用AI服务未知异常: {str(e)}")
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            quiz.status = 'failed'
            quiz.error_message = f'生成失败：{str(e)}'
            quiz.save()
            return
    
    questions_data=data.get('questions',[])
    if not questions_data:
        quiz.status='failed'
        quiz.error_message='ai服务返回空数据'
        quiz.save()
        return
    for q_data in questions_data:
        Question.objects.create(
            quiz=quiz,
            stem=q_data['stem'],
            options=q_data['options'],
            answer=q_data.get('answer',''),
            explanation=q_data.get('explanation',''),
        )
    quiz.status='completed'
    quiz.save()
    logger.info(f'Quiz {quiz_id} 生成完成,共{len(questions_data)}题')


