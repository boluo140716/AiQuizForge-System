"""SM-2 间隔重复调度。"""
import logging
from datetime import timedelta

from django.utils import timezone

from notes.models import ReviewSchedule

logger = logging.getLogger(__name__)

MIN_EF, MAX_EF = 1.3, 2.5


def sm2_next(ease_factor: float, interval_days: int, repetitions: int,
             lapses: int, quality: int):
    """SM-2 核心：返回 (新 EF, 新间隔天数, 新连续答对次数, 新遗忘次数)。

    quality：0-5。答对用 4，答错用 2。
    - EF' = EF + (0.1 - (5-q)(0.08 + (5-q)×0.02))，限制在 [1.3, 2.5]
    - q < 3：重置（间隔 1 天，连续答对清零，遗忘 +1）
    - 否则：间隔 1 → 6 → round(上次间隔 × EF')
    """
    q = max(0, min(5, quality))
    ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(MIN_EF, min(MAX_EF, ef))

    if q < 3:
        return ef, 1, 0, lapses + 1

    reps = repetitions + 1
    if reps == 1:
        interval = 1
    elif reps == 2:
        interval = 6
    else:
        interval = max(1, round(interval_days * ef))
    return ef, interval, reps, lapses


def update_review_schedule(user, question, is_correct: bool):
    """答题后更新排程。question 必须是原始题（不是复习卷里的副本）。"""
    quality = 4 if is_correct else 2
    obj, _ = ReviewSchedule.objects.get_or_create(
        user=user,
        question=question,
        defaults={"due_at": timezone.now()},
    )
    ef, interval, reps, lapses = sm2_next(
        obj.ease_factor, obj.interval_days, obj.repetitions, obj.lapses, quality
    )

    now = timezone.now()
    obj.ease_factor = ef
    obj.interval_days = interval
    obj.repetitions = reps
    obj.lapses = lapses
    obj.last_reviewed_at = now
    obj.due_at = now + timedelta(days=interval)
    obj.save(update_fields=[
        "ease_factor", "interval_days", "repetitions",
        "lapses", "last_reviewed_at", "due_at",
    ])

    logger.info(
        "SM-2 更新 user=%s question=%s correct=%s -> interval=%s due=%s",
        user.id, question.id, is_correct, interval, obj.due_at,
    )
    return obj
