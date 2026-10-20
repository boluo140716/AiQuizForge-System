"""BKT（贝叶斯知识追踪）：维护"用户 × 知识点"的掌握概率。"""
import logging

from notes.bkt import bkt_update
from notes.models import UserKPMastery

logger = logging.getLogger(__name__)


def update_mastery(user, kp, is_correct: bool) -> float:
    """按一次答题结果更新掌握度，返回更新后的 p。"""
    obj, _ = UserKPMastery.objects.get_or_create(user=user, kp=kp)
    old_p = obj.p_mastery

    new_p = bkt_update(
        old_p,
        is_correct,
        p_transit=obj.p_transit,
        p_slip=obj.p_slip,
        p_guess=obj.p_guess,
    )

    obj.p_mastery = new_p
    obj.attempts += 1
    if is_correct:
        obj.correct += 1
    obj.save(update_fields=["p_mastery", "attempts", "correct", "updated_at"])

    logger.info(
        "BKT 更新 user=%s kp=%s correct=%s: %.3f -> %.3f",
        user.id, kp.id, is_correct, old_p, new_p,
    )
    return new_p
