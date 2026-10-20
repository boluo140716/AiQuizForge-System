"""E2 实验：自适应选题 vs 随机选题（模拟学生）。

运行（项目根目录）：
    python backend/scripts/simulate_e2.py --students 50 --rounds 10 --questions 5 \
        --kps 20 --per-kp 3 --seed 42 --learn-rate 0.08 --bkt-transit 0.03 \
        --adaptive-strategy ucb --out reports/e2_learning

输出：
    <out>/e2_result.csv   每个学生的指标（配对数据）
    <out>/e2_report.md    汇总报告（含 95% CI）
    <out>/e2_curve.csv    每轮的平均后测正确率（学习曲线）

说明：
- 观测模型：P(答对) = θ(1-slip) + (1-θ)guess
- 学习模型：θ += (1-θ) × learn_rate × ZPD（ZPD=1-|θ-0.5|×2）
  即"练习收益在最近发展区最大"，这是本模拟的核心假设，报告中会明确写出。
- 选题策略：random / zpd（ε-greedy）/ ucb（ZPD + 探索奖励）
- 同一学生用同一初始 θ 和同一套后测题，分别跑两种策略（配对比较）。
"""
import argparse
import csv
import math
import os
import random
import statistics
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from notes.bkt import bkt_update                       # noqa: E402
from notes.scoring import question_score, zpd_factor   # noqa: E402

P_SLIP = 0.10
P_GUESS = 0.25
P_TRANSIT = 0.15
LEARN_RATE = 0.06
BKT_TRANSIT = P_TRANSIT
EPSILON = 0.15
COVERAGE_WEIGHT = 0.3
UCB_C = 0.5


def p_correct(theta: float) -> float:
    return theta * (1 - P_SLIP) + (1 - theta) * P_GUESS


def learn(theta: float, model: str = "zpd") -> float:
    if model == "zpd":
        factor = max(0.0, 1.0 - abs(theta - 0.5) * 2.0)
    else:
        factor = 1.0
    return min(0.99, theta + (1 - theta) * LEARN_RATE * factor)


def elo_to_p(elo: float, difficulty: float = 1500.0) -> float:
    return 1.0 / (1.0 + 10 ** ((difficulty - elo) / 400.0))


def elo_to_theta(elo: float) -> float:
    """把 Elo 期望正确率反推成掌握度估计。"""
    p = elo_to_p(elo)
    return max(0.001, min(0.999, (p - P_GUESS) / (1 - P_SLIP - P_GUESS)))


def build_bank(kps: int, per_kp: int):
    bank, qid = [], 0
    for kp in range(kps):
        for _ in range(per_kp):
            bank.append({"id": qid, "kp": kp})
            qid += 1
    return bank


def select_zpd(bank, mastery, count, rng):
    """纯 ZPD + ε-greedy + 覆盖奖励。"""
    candidates = list(bank)
    selected, covered = [], set()
    while candidates and len(selected) < count:
        if rng.random() < EPSILON:
            q = rng.choice(candidates)
            candidates.remove(q)
        else:
            best_i, best_s = -1, -1.0
            for i, item in enumerate(candidates):
                s = question_score(mastery, [item["kp"]], covered,
                                   coverage_weight=COVERAGE_WEIGHT)
                if s > best_s:
                    best_s, best_i = s, i
            q = candidates.pop(best_i)
        selected.append(q)
        covered.add(q["kp"])
    return selected


def select_ucb(bank, mastery, pulls, count, rng):
    """UCB：ZPD 利用 + 对"练得少"的知识点给探索奖励。"""
    candidates = list(bank)
    selected = []
    total = sum(pulls) + 1
    while candidates and len(selected) < count:
        if rng.random() < EPSILON:
            q = rng.choice(candidates)
            candidates.remove(q)
        else:
            best_i, best_s = -1, -1.0
            for i, item in enumerate(candidates):
                kp = item["kp"]
                bonus = UCB_C * math.sqrt(math.log(total + 1) / (pulls[kp] + 1))
                s = zpd_factor(mastery.get(kp, 0.3)) + bonus
                if s > best_s:
                    best_s, best_i = s, i
            q = candidates.pop(best_i)
        selected.append(q)
    return selected


def select_oracle(bank, theta, count):
    """上界对照：直接用真实掌握度选题（现实中不可得，仅用于验证方法本身）。"""
    mastery = {k: theta[k] for k in range(len(theta))}
    candidates = list(bank)
    selected = []
    while candidates and len(selected) < count:
        best_i, best_s = -1, -1.0
        for i, item in enumerate(candidates):
            s = zpd_factor(mastery[item["kp"]])
            if s > best_s:
                best_s, best_i = s, i
        selected.append(candidates.pop(best_i))
    return selected


def sample_theta(rng, kps, dist="uniform"):
    """生成学生的初始掌握度分布。bimodal 更贴近"多数很难/很容易、少数在中游"的现实。"""
    if dist == "bimodal":
        values = []
        for _ in range(kps):
            u = rng.random()
            if u < 0.4:
                values.append(rng.uniform(0.05, 0.25))
            elif u < 0.8:
                values.append(rng.uniform(0.75, 0.95))
            else:
                values.append(rng.uniform(0.40, 0.60))
        return values
    return [rng.uniform(0.05, 0.95) for _ in range(kps)]


def run_student(seed: int, kps: int, bank, rounds: int, per_round: int,
                strategy: str, learning_model: str, test_per_kp: int = 3,
                theta_dist: str = "uniform", estimator: str = "bkt"):
    rng = random.Random(seed)
    test_rng = random.Random(seed ^ 0x5DEECE66D)

    theta = sample_theta(rng, kps, theta_dist)
    est = [0.30] * kps
    elo = [1500.0] * kps
    pulls = [0] * kps

    test_set = [
        (kp, test_rng.random())
        for kp in range(kps)
        for _ in range(test_per_kp)
    ]

    def accuracy(kp_subset=None) -> float:
        items = [(kp, u) for kp, u in test_set if kp_subset is None or kp in kp_subset]
        hits = sum(1 for kp, u in items if u < p_correct(theta[kp]))
        return hits / len(items) if items else 0.0

    weak_kps = [k for k in range(kps) if theta[k] < 0.6]
    pre_acc = accuracy()
    pre_weak = accuracy(weak_kps)

    curve = []
    practiced = set()
    zpd_sum = 0.0
    exposures = 0

    for _ in range(rounds):
        if strategy == "random":
            selected = rng.sample(bank, min(per_round, len(bank)))
        elif strategy == "oracle":
            selected = select_oracle(bank, theta, per_round)
        elif strategy == "ucb":
            selected = select_ucb(bank, {k: est[k] for k in range(kps)}, pulls, per_round, rng)
        else:
            selected = select_zpd(bank, {k: est[k] for k in range(kps)}, per_round, rng)

        for q in selected:
            kp = q["kp"]
            pulls[kp] += 1
            zpd_sum += zpd_factor(theta[kp])
            exposures += 1

            correct = rng.random() < p_correct(theta[kp])
            if estimator == "elo":
                expected = elo_to_p(elo[kp])
                elo[kp] += 32.0 * ((1.0 if correct else 0.0) - expected)
                est[kp] = elo_to_theta(elo[kp])
            else:
                est[kp] = bkt_update(est[kp], correct, BKT_TRANSIT, P_SLIP, P_GUESS)
            theta[kp] = learn(theta[kp], learning_model)
            practiced.add(kp)

        curve.append(accuracy())

    post_acc = accuracy()
    post_weak = accuracy(weak_kps)
    mae = sum(abs(est[k] - theta[k]) for k in range(kps)) / kps

    return {
        "pre_acc": pre_acc,
        "post_acc": post_acc,
        "gain": post_acc - pre_acc,
        "weak_gain": post_weak - pre_weak,
        "mae": mae,
        "coverage": len(practiced) / kps,
        "avg_zpd": (zpd_sum / exposures) if exposures else 0.0,
        "curve": curve,
    }


def mean_std(values):
    return statistics.mean(values), (statistics.pstdev(values) if len(values) > 1 else 0.0)


def paired_ci(diffs):
    n = len(diffs)
    if n < 2:
        return 0.0, 0.0
    m = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    return m, 1.96 * (sd / math.sqrt(n))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--students", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--questions", type=int, default=5)
    parser.add_argument("--kps", type=int, default=10)
    parser.add_argument("--per-kp", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-model", choices=["zpd", "uniform"], default="zpd")
    parser.add_argument("--learn-rate", type=float, default=0.06)
    parser.add_argument("--bkt-transit", type=float, default=P_TRANSIT)
    parser.add_argument("--epsilon", type=float, default=0.15)
    parser.add_argument("--coverage-weight", type=float, default=0.3)
    parser.add_argument("--theta-dist", choices=["uniform", "bimodal"], default="uniform")
    parser.add_argument("--estimator", choices=["bkt", "elo"], default="bkt")
    parser.add_argument("--adaptive-strategy", choices=["zpd", "ucb", "oracle"], default="zpd")
    parser.add_argument("--out", default="reports")
    args = parser.parse_args()

    global LEARN_RATE, BKT_TRANSIT, EPSILON, COVERAGE_WEIGHT
    LEARN_RATE = args.learn_rate
    BKT_TRANSIT = args.bkt_transit
    EPSILON = args.epsilon
    COVERAGE_WEIGHT = args.coverage_weight

    rng = random.Random(args.seed)
    bank = build_bank(args.kps, args.per_kp)
    os.makedirs(args.out, exist_ok=True)

    rows, curves_a, curves_r = [], [], []
    for sid in range(args.students):
        seed = rng.randrange(10 ** 9)
        a = run_student(seed, args.kps, bank, args.rounds, args.questions,
                        args.adaptive_strategy, args.learning_model,
                        theta_dist=args.theta_dist, estimator=args.estimator)
        r = run_student(seed, args.kps, bank, args.rounds, args.questions,
                        "random", args.learning_model,
                        theta_dist=args.theta_dist, estimator=args.estimator)
        rows.append({
            "student": sid,
            **{f"adaptive_{k}": v for k, v in a.items() if k != "curve"},
            **{f"random_{k}": v for k, v in r.items() if k != "curve"},
        })
        curves_a.append(a["curve"])
        curves_r.append(r["curve"])

    csv_path = os.path.join(args.out, "e2_result.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    curve_path = os.path.join(args.out, "e2_curve.csv")
    with open(curve_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["round", "adaptive_acc", "random_acc"])
        for i in range(args.rounds):
            writer.writerow([
                i + 1,
                sum(c[i] for c in curves_a) / len(curves_a),
                sum(c[i] for c in curves_r) / len(curves_r),
            ])

    lines = [
        "# E2 实验：自适应 vs 随机选题（模拟）",
        "",
        f"- 学生数：{args.students}",
        f"- 训练轮数：{args.rounds}，每轮题数：{args.questions}",
        f"- 知识点数：{args.kps}，每知识点题库：{args.per_kp}",
        f"- 随机种子：{args.seed}",
        f"- 自适应策略：{args.adaptive_strategy}",
        f"- 学习模型：{args.learning_model}，真实学习率：{args.learn_rate}",
        f"- BKT 估计用转移概率：{args.bkt_transit}",
        "",
        "> 观测模型：`P(答对)=θ(1-slip)+(1-θ)guess`；学习模型：`θ += (1-θ)×learn_rate×ZPD`"
        "（`ZPD=1-|θ-0.5|×2`，即练习收益在最近发展区最大）。",
        "",
        "| 指标 | 自适应 | 随机 | 配对差异 (自适应-随机) | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for m in ["pre_acc", "post_acc", "gain", "weak_gain", "mae", "coverage", "avg_zpd"]:
        a_vals = [row[f"adaptive_{m}"] for row in rows]
        r_vals = [row[f"random_{m}"] for row in rows]
        a_mean, a_std = mean_std(a_vals)
        r_mean, r_std = mean_std(r_vals)
        d_mean, ci = paired_ci([x - y for x, y in zip(a_vals, r_vals)])
        lines.append(
            f"| {m} | {a_mean:.4f} ± {a_std:.4f} | {r_mean:.4f} ± {r_std:.4f} | "
            f"{d_mean:+.4f} | ±{ci:.4f} |"
        )
    lines += [
        "",
        f"明细：`{csv_path}`；学习曲线：`{curve_path}`",
    ]

    report_path = os.path.join(args.out, "e2_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\n已写入：{report_path}")


if __name__ == "__main__":
    main()
