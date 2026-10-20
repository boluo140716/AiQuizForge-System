"""E2 汇总实验：一次跑四种选题策略，输出对比表。

运行（项目根目录）：
    python backend/scripts/compare_e2.py --students 50 --rounds 10 --questions 5 \
        --kps 20 --per-kp 3 --seed 42 --learn-rate 0.08 --bkt-transit 0.03 \
        --out reports/e2_compare

输出：
    <out>/e2_compare.md    四种策略的对比表（均值 ± 标准差，以及相对随机的配对差异 + 95% CI）
    <out>/e2_compare.csv   每个学生 × 每种策略的明细
    <out>/e2_curve.csv     各策略每轮的平均正确率
"""
import argparse
import csv
import math
import os
import random
import statistics
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

import simulate_e2 as sim  # noqa: E402

STRATEGIES = ["random", "zpd", "ucb", "oracle"]
METRICS = ["pre_acc", "post_acc", "gain", "weak_gain", "mae", "coverage", "avg_zpd"]


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
    parser.add_argument("--kps", type=int, default=20)
    parser.add_argument("--per-kp", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-model", choices=["zpd", "uniform"], default="zpd")
    parser.add_argument("--learn-rate", type=float, default=0.08)
    parser.add_argument("--bkt-transit", type=float, default=0.03)
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--coverage-weight", type=float, default=0.15)
    parser.add_argument("--out", default="reports/e2_compare")
    args = parser.parse_args()

    # 覆盖 simulate_e2 的模块级参数
    sim.LEARN_RATE = args.learn_rate
    sim.BKT_TRANSIT = args.bkt_transit
    sim.EPSILON = args.epsilon
    sim.COVERAGE_WEIGHT = args.coverage_weight

    rng = random.Random(args.seed)
    bank = sim.build_bank(args.kps, args.per_kp)
    os.makedirs(args.out, exist_ok=True)

    rows = []
    curves = {s: [] for s in STRATEGIES}

    for sid in range(args.students):
        seed = rng.randrange(10 ** 9)
        row = {"student": sid}
        for strategy in STRATEGIES:
            result = sim.run_student(
                seed, args.kps, bank, args.rounds, args.questions,
                strategy, args.learning_model,
            )
            curves[strategy].append(result["curve"])
            for m in METRICS:
                row[f"{strategy}_{m}"] = result[m]
        rows.append(row)

    csv_path = os.path.join(args.out, "e2_compare.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    curve_path = os.path.join(args.out, "e2_curve.csv")
    with open(curve_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["round"] + STRATEGIES)
        for i in range(args.rounds):
            writer.writerow(
                [i + 1] + [sum(c[i] for c in curves[s]) / len(curves[s]) for s in STRATEGIES]
            )

    lines = [
        "# E2 汇总实验：四种选题策略对比（模拟）",
        "",
        f"- 学生数：{args.students}；训练轮数：{args.rounds}；每轮题数：{args.questions}",
        f"- 知识点数：{args.kps}；每知识点题库：{args.per_kp}；随机种子：{args.seed}",
        f"- 学习模型：{args.learning_model}，真实学习率：{args.learn_rate}；BKT transit：{args.bkt_transit}",
        f"- ε：{args.epsilon}；覆盖权重：{args.coverage_weight}",
        "",
        "> 策略说明：`random` 随机选题；`zpd` 纯最近发展区 + ε-greedy；`ucb` ZPD + 上置信界探索；"
        "`oracle` 用真实掌握度选题（理论上界，现实中不可得）。",
        "",
        "## 均值 ± 标准差",
        "",
        "| 策略 | post_acc | gain | weak_gain | coverage | avg_zpd | mae |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in STRATEGIES:
        vals = []
        for m in ["post_acc", "gain", "weak_gain", "coverage", "avg_zpd", "mae"]:
            mean, std = mean_std([r[f"{s}_{m}"] for r in rows])
            vals.append(f"{mean:.4f} ± {std:.4f}")
        lines.append(f"| {s} | " + " | ".join(vals) + " |")

    lines += [
        "",
        "## 相对随机的配对差异（95% CI）",
        "",
        "| 策略 | Δgain | Δweak_gain | Δmae | Δcoverage | Δavg_zpd |",
        "|---|---|---|---|---|---|",
    ]
    for s in ["zpd", "ucb", "oracle"]:
        cells = []
        for m in ["gain", "weak_gain", "mae", "coverage", "avg_zpd"]:
            diffs = [r[f"{s}_{m}"] - r[f"random_{m}"] for r in rows]
            d_mean, ci = paired_ci(diffs)
            cells.append(f"{d_mean:+.4f} (±{ci:.4f})")
        lines.append(f"| {s} | " + " | ".join(cells) + " |")

    lines += [
        "",
        f"明细：`{csv_path}`；学习曲线：`{curve_path}`",
    ]

    report_path = os.path.join(args.out, "e2_compare.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\n已写入：{report_path}")


if __name__ == "__main__":
    main()
