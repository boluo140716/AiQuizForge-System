"""从 E1 题目明细生成人工标注模板（供计算 judge 与人工的一致性 κ）。"""
import argparse
import csv

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="reports/e1/e1_questions.csv")
parser.add_argument("--output", default="reports/e1/human_labels.csv")
parser.add_argument("--limit", type=int, default=40)
args = parser.parse_args()

rows = []
with open(args.input, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= args.limit:
            break
        rows.append({
            "config": row["config"],
            "note_id": row["note_id"],
            "index": row["index"],
            "stem": row["stem"],
            "groundedness_human": "",
            "distractor_human": "",
            "unambiguity_human": "",
        })

with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"已生成人工标注模板：{args.output}（{len(rows)} 行，请填 1-5 分）")
