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
        with httpx.Client(timeout=60) as client:
            response = client.post(ai_service_url, headers=headers, json=payload)
            response.raise_for_status()
            data=response.json()
    except httpx.HTTPError as e:
        logger.error(f"ai服务返回错误: {e.response.status_code}:{e.response.text}")
        quiz.status='failed'
        quiz.error_message=f"Ai服务调用失败: {e.response.status_code}"
        quiz.save()
        return
    except Exception as e:
        logger.error(f"ai服务调用异常: {str(e)}")
        self.retry(exc=e,countdown=60)
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


