"""轻量可观测性：健康检查 + Prometheus 文本指标。

不引入额外依赖，便于在课程/毕业设计环境中直接部署。
如果设置了环境变量 METRICS_TOKEN，则 /metrics/ 需要请求头 X-Metrics-Token 匹配。
"""
import os
import time

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.http import HttpResponse, JsonResponse

from notes.models import FailedTask, Note, Question, Quiz

START_TIME = time.time()


def _db_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except Exception:
        return False


def _redis_ok():
    try:
        cache.set("__healthcheck__", "1", 5)
        return cache.get("__healthcheck__") == "1"
    except Exception:
        return False


def health_view(request):
    """GET /health/ —— 供 Docker/负载均衡做存活与就绪检查。"""
    db_ok = _db_ok()
    redis_ok = _redis_ok()
    healthy = db_ok and redis_ok
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "db": db_ok,
            "redis": redis_ok,
            "uptime_seconds": round(time.time() - START_TIME, 1),
        },
        status=200 if healthy else 503,
    )


def _metrics_authorized(request):
    token = os.getenv("METRICS_TOKEN", "")
    return not token or request.headers.get("X-Metrics-Token") == token


def metrics_view(request):
    """GET /metrics/ —— Prometheus 文本格式指标。"""
    if not _metrics_authorized(request):
        return HttpResponse("forbidden\n", status=403, content_type="text/plain")

    db_ok = _db_ok()
    redis_ok = _redis_ok()

    lines = [
        "# HELP quizforge_up 服务是否存活",
        "# TYPE quizforge_up gauge",
        "quizforge_up 1",
        "# HELP quizforge_db_up 数据库是否可用",
        "# TYPE quizforge_db_up gauge",
        f"quizforge_db_up {int(db_ok)}",
        "# HELP quizforge_redis_up Redis 是否可用",
        "# TYPE quizforge_redis_up gauge",
        f"quizforge_redis_up {int(redis_ok)}",
        "# HELP quizforge_uptime_seconds 进程运行时长（秒）",
        "# TYPE quizforge_uptime_seconds gauge",
        f"quizforge_uptime_seconds {time.time() - START_TIME:.1f}",
    ]

    if db_ok:
        try:
            status_counts = dict(
                Quiz.objects.values_list("status").annotate(n=Count("id"))
            )
            lines += [
                "# HELP quizforge_notes_total 笔记总数",
                "# TYPE quizforge_notes_total gauge",
                f"quizforge_notes_total {Note.objects.count()}",
                "# HELP quizforge_questions_total 题目总数",
                "# TYPE quizforge_questions_total gauge",
                f"quizforge_questions_total {Question.objects.count()}",
                "# HELP quizforge_quizzes_total 按状态统计的测验数",
                "# TYPE quizforge_quizzes_total gauge",
            ]
            for quiz_status in ("processing", "completed", "failed"):
                lines.append(
                    f'quizforge_quizzes_total{{status="{quiz_status}"}} '
                    f"{status_counts.get(quiz_status, 0)}"
                )
            lines += [
                "# HELP quizforge_failed_tasks_total 失败任务留档数",
                "# TYPE quizforge_failed_tasks_total gauge",
                f"quizforge_failed_tasks_total {FailedTask.objects.count()}",
            ]
        except Exception:
            # 指标采集失败不应影响服务本身
            pass

    return HttpResponse(
        "\n".join(lines) + "\n",
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )
