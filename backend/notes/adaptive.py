"""自适应选题：按知识点掌握度（最近发展区）挑选题目。"""
import logging

from notes.models import Question, UserKPMastery
from notes.scoring import question_score

logger = logging.getLogger(__name__)


def _mastery_map(user):
    return dict(
        UserKPMastery.objects.filter(user=user).values_list("kp_id", "p_mastery")
    )


def _question_score(question, mastery, covered_kp_ids):
    kp_ids = [link.kp_id for link in question.kp_links.all()]
    return question_score(mastery, kp_ids, covered_kp_ids)


def select_adaptive_questions(user, *, note=None, notebook=None, count=5):
    """贪心选择：优先掌握度接近 0.5 的 KP，并尽量覆盖不同 KP。

    返回 (选中的题目列表, 覆盖到的 kp_id 集合)。
    """
    qs = (
        Question.objects.filter(quiz__user=user, quiz__status="completed")
        .prefetch_related("kp_links__kp")
        .order_by("-id")
    )
    if note is not None:
        qs = qs.filter(quiz__note=note)
    if notebook is not None:
        qs = qs.filter(quiz__note__notebook_id=notebook.id)

    # 按题干去重（重练/多次生成可能产生副本）
    seen = set()
    candidates = []
    for q in qs:
        key = (q.stem or "").strip()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(q)

    mastery = _mastery_map(user)
    selected = []
    covered = set()

    while candidates and len(selected) < count:
        best_idx = -1
        best_score = -1.0
        for i, q in enumerate(candidates):
            score = _question_score(q, mastery, covered)
            if score > best_score:
                best_score = score
                best_idx = i
        q = candidates.pop(best_idx)
        selected.append(q)
        for link in q.kp_links.all():
            covered.add(link.kp_id)

    return selected, covered
