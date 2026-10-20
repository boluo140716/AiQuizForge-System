"""计算 LLM judge 与人工标注的一致性：二次加权 Cohen's κ + Spearman 相关。

用法：
1. 先运行 evaluate_ablation.py 生成 reports/e1/e1_questions.csv
2. 运行 make_label_template.py 生成 human_labels.csv
3. 人工填好 1-5 分后运行：
   python ai_service/scripts/compute_kappa.py \
     --judge reports/e1/e1_questions.csv \
     --human reports/e1/human_labels.csv

判定参考：κ < 0.4 不可信；0.4-0.6 中等；0.6-0.8 较好；> 0.8 很好。
"""
import argparse
import csv
import math

DIMENSIONS = ["groundedness", "distractor", "unambiguity"]


def load_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def weighted_kappa(y1, y2, k=5):
    """二次加权 Cohen's κ（评分 1..k）。"""
    n = len(y1)
    if n == 0:
        return 0.0
    # 混淆矩阵
    O = [[0] * k for _ in range(k)]
    for a, b in zip(y1, y2):
        O[a - 1][b - 1] += 1
    # 边际分布
    hist1 = [sum(O[i]) for i in range(k)]
    hist2 = [sum(O[i][j] for i in range(k)) for j in range(k)]
    # 期望矩阵
    E = [[hist1[i] * hist2[j] / n for j in range(k)] for i in range(k)]
    # 二次权重
    W = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    num = sum(W[i][j] * O[i][j] for i in range(k) for j in range(k))
    den = sum(W[i][j] * E[i][j] for i in range(k) for j in range(k))
    return 1.0 - num / den if den else 0.0


def rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(x, y):
    if len(x) < 2:
        return 0.0
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    return cov / math.sqrt(vx * vy) if vx and vy else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", default="reports/e1/e1_questions.csv")
    parser.add_argument("--human", default="reports/e1/human_labels.csv")
    args = parser.parse_args()

    judge_rows = load_csv(args.judge)
    human_rows = load_csv(args.human)

    judge_map = {
        (r["config"], r["note_id"], r["index"]): r for r in judge_rows
    }

    print(f"{'维度':<14}{'样本数':>6}{'加权κ':>10}{'Spearman':>12}")
    for dim in DIMENSIONS:
        j_vals, h_vals = [], []
        for h in human_rows:
            key = (h["config"], h["note_id"], h["index"])
            j = judge_map.get(key)
            if not j:
                continue
            jv = j.get(dim, "")
            hv = h.get(f"{dim}_human", "")
            if jv == "" or hv == "":
                continue
            try:
                j_vals.append(max(1, min(5, round(float(jv) * 4 + 1))))
                h_vals.append(max(1, min(5, int(float(hv)))))
            except ValueError:
                continue

        if not j_vals:
            print(f"{dim:<14}{0:>6}{'-':>10}{'-':>12}")
            continue
        kappa = weighted_kappa(j_vals, h_vals)
        rho = spearman(j_vals, h_vals)
        print(f"{dim:<14}{len(j_vals):>6}{kappa:>10.3f}{rho:>12.3f}")


if __name__ == "__main__":
    main()
