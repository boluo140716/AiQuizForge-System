"""自适应选题打分（纯函数，不依赖 Django）。"""
DEFAULT_MASTERY = 0.30
TARGET_MASTERY = 0.5


def zpd_factor(p: float, target: float = TARGET_MASTERY) -> float:
    """最近发展区因子：掌握度越接近 target，分数越高（0.5 -> 1，0/1 -> 0）。"""
    return max(0.0, 1.0 - abs(p - target) * 2.0)


def question_score(kp_masteries: dict, kp_ids, covered_kp_ids,
                   default: float = DEFAULT_MASTERY,
                   target: float = TARGET_MASTERY,
                   coverage_weight: float = 0.3) -> float:
    """一道题的得分：掌握度接近 target 优先，同时奖励未覆盖的知识点。

    coverage_weight 越大越鼓励"覆盖新知识点"；越小越专注"最近发展区"。
    """
    if not kp_ids:
        return 0.1  # 没打标签的题，低优先级

    best = 0.0
    for kp_id in kp_ids:
        p = kp_masteries.get(kp_id, default)
        coverage = 1.0 if kp_id not in covered_kp_ids else 0.0
        best = max(
            best,
            (1.0 - coverage_weight) * zpd_factor(p, target)
            + coverage_weight * coverage,
        )
    return best
