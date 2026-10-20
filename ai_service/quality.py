"""题目质量门控：在题目入库前，把明显不合格的题剔掉。

只做"确定性规则"检查（便宜、可解释）；更高级的语义质量评估留给第 6 章的
LLM-as-judge 评估流水线。
"""
import difflib
import re

_BANNED_OPTIONS = ('以上都对', '以上都不对', '以上皆是', '以上皆非', '都正确', '都不正确')
_OPTION_PREFIX = re.compile(r'^\s*[A-Da-d][\.、:：\)）]\s*')


def _norm(text: str) -> str:
    return re.sub(r'\s+', '', (text or '')).strip().lower()


def check_question(q: dict) -> list[str]:
    """返回问题列表；空列表表示通过。"""
    issues: list[str] = []
    stem = (q.get('stem') or '').strip()
    options = q.get('options') or []
    answer = (q.get('answer') or '').strip().upper()

    if len(stem) < 5:
        issues.append('题干过短')
    if len(options) != 4:
        issues.append('选项不是 4 个')
    if answer not in ('A', 'B', 'C', 'D'):
        issues.append('答案不是 A-D')

    cleaned = []
    for opt in options:
        o = _OPTION_PREFIX.sub('', (opt or '')).strip()
        if not o:
            issues.append('存在空选项')
        cleaned.append(o)

    if len(set(_norm(o) for o in cleaned)) != len(cleaned):
        issues.append('存在重复选项')

    for o in cleaned:
        if any(b in o for b in _BANNED_OPTIONS):
            issues.append('使用了万能选项')

    # 选项之间过于相似（>0.9）视为无效
    too_similar = False
    for i in range(len(cleaned)):
        for j in range(i + 1, len(cleaned)):
            if cleaned[i] and cleaned[j]:
                if difflib.SequenceMatcher(None, cleaned[i], cleaned[j]).ratio() > 0.9:
                    too_similar = True
                    break
        if too_similar:
            break
    if too_similar:
        issues.append('选项过于相似')

    # 题干与选项重复
    if stem and any(_norm(stem) == _norm(o) for o in cleaned):
        issues.append('题干与选项重复')

    return issues


def filter_by_quality(questions: list[dict]):
    """拆成 (通过的题目, 被剔除的 [(题目, 原因)])。"""
    kept, dropped = [], []
    for q in questions:
        issues = check_question(q)
        if issues:
            dropped.append((q, issues))
        else:
            kept.append(q)
    return kept, dropped


def log_dropped(dropped, logger) -> None:
    if not dropped:
        return
    logger.info("质量门控：剔除 %d 道不合格题目", len(dropped))
    for q, issues in dropped[:5]:
        logger.info("  剔除: %s | %s", (q.get('stem') or '')[:30], issues)
