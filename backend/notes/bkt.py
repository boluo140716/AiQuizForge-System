"""BKT 数学核心（纯函数，不依赖 Django）。

生产代码（notes/mastery.py）与实验脚本（scripts/simulate_e2.py）共用这套公式，
保证"论文实验验证的就是系统实际使用的算法"。
"""
MIN_P, MAX_P = 0.001, 0.999


def clamp(p: float) -> float:
    return max(MIN_P, min(MAX_P, p))


def bkt_update(p: float, is_correct: bool,
               p_transit: float = 0.15,
               p_slip: float = 0.10,
               p_guess: float = 0.25) -> float:
    """一次答题后的掌握度更新。

    答对：post = p(1-slip) / [p(1-slip) + (1-p)guess]
    答错：post = p*slip    / [p*slip    + (1-p)(1-guess)]
    再叠加学习转移：p' = post + (1-post)*transit
    """
    p = clamp(p)

    if is_correct:
        denom = p * (1 - p_slip) + (1 - p) * p_guess
        post = (p * (1 - p_slip)) / denom if denom else p
    else:
        denom = p * p_slip + (1 - p) * (1 - p_guess)
        post = (p * p_slip) / denom if denom else p

    return clamp(post + (1 - post) * p_transit)
