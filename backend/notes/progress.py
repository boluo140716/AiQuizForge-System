"""生成进度广播：用 Redis Pub/Sub 给 SSE 提供实时进度。

- 任务执行过程中调用 publish_progress() 发消息；
- SSE 接口订阅同一个频道，把消息推给浏览器；
- 同时把最新状态写进一个带 TTL 的 key，供 SSE 重连时补发。
"""
import json
import logging

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

PROGRESS_CHANNEL = "quiz:{quiz_id}:progress"
PROGRESS_STATE_KEY = "quiz:{quiz_id}:state"
PROGRESS_TTL = 3600


def get_redis():
    """Django 侧访问 Redis（db=2，与 ai_service 的进度/缓存保持一致）。"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        password=settings.REDIS_PASSWORD or None,
        db=2,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def publish_progress(quiz_id: int, payload: dict) -> None:
    """写最新状态 + 发布到频道。失败只记日志，不能影响主流程。"""
    data = json.dumps(payload, ensure_ascii=False)
    try:
        r = get_redis()
        r.set(PROGRESS_STATE_KEY.format(quiz_id=quiz_id), data, ex=PROGRESS_TTL)
        r.publish(PROGRESS_CHANNEL.format(quiz_id=quiz_id), data)
        r.close()
    except Exception as e:
        logger.warning("发布进度失败 quiz=%s: %s", quiz_id, e)


def get_progress(quiz_id: int):
    try:
        r = get_redis()
        value = r.get(PROGRESS_STATE_KEY.format(quiz_id=quiz_id))
        r.close()
        return value
    except Exception as e:
        logger.warning("读取进度失败 quiz=%s: %s", quiz_id, e)
        return None
