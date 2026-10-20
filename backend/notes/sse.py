"""SSE：实时推送测验生成进度。"""
import json
import logging
import time

from django.http import HttpResponse, StreamingHttpResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from notes.models import Quiz
from notes.progress import PROGRESS_CHANNEL, get_progress, get_redis

logger = logging.getLogger(__name__)


def quiz_progress_stream(request, quiz_id: int):
    """GET /api/v1/quizzes/<quiz_id>/stream/?token=<access_token>

    认证说明：浏览器的 EventSource 不能自定义请求头，所以 token 走 query 参数。
    （生产环境可换成短期签名票据或 Cookie，避免 token 出现在 URL 日志里。）
    """
    token = request.GET.get("token", "")
    try:
        access = AccessToken(token)
        user_id = access["user_id"]
    except TokenError:
        return HttpResponse(status=401)

    try:
        quiz = Quiz.objects.get(id=quiz_id, user_id=user_id)
    except Quiz.DoesNotExist:
        return HttpResponse(status=404)

    def fallback_payload() -> str:
        raw = get_progress(quiz_id)
        if raw:
            return raw
        return json.dumps(
            {
                "stage": quiz.status,
                "done": 1 if quiz.status == "completed" else 0,
                "total": 1,
                "message": quiz.error_message or "",
            },
            ensure_ascii=False,
        )

    def event_stream():
        # 1) 连上先补发当前状态
        yield f"data: {fallback_payload()}\n\n"
        if quiz.status in ("completed", "failed"):
            return

        # 2) 订阅进度频道
        r = get_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(PROGRESS_CHANNEL.format(quiz_id=quiz_id))
        last_ping = time.time()
        try:
            while True:
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=5)
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    yield f"data: {data}\n\n"
                    try:
                        stage = json.loads(data).get("stage")
                    except Exception:
                        stage = None
                    if stage in ("done", "failed"):
                        break
                else:
                    # 3) 心跳：防止代理/浏览器判定连接空闲
                    if time.time() - last_ping >= 15:
                        yield ": ping\n\n"
                        last_ping = time.time()

                    # 4) 兜底：即使 Redis 消息丢了，也以数据库终态为准
                    row = (
                        Quiz.objects.filter(id=quiz_id)
                        .values("status", "progress", "error_message")
                        .first()
                    )
                    if row and row["status"] in ("completed", "failed"):
                        payload = row["progress"] or {
                            "stage": row["status"],
                            "done": 1,
                            "total": 1,
                            "message": row["error_message"] or "",
                        }
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        break
        finally:
            try:
                pubsub.close()
            except Exception:
                pass
            try:
                r.close()
            except Exception:
                pass

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"   # 让 Nginx 不要缓冲 SSE
    return response
