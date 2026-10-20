"""E1 消融实验：不同提示词/约束配置下的题目质量对比。

在 ai-service 容器内运行（需要真实 LLM_API_KEY）：
    docker compose run --rm --no-deps --entrypoint python \
      -v "<project>/ai_service:/app" -v "<project>/reports:/reports" \
      ai-service scripts/evaluate_ablation.py --limit 3 --count 3 --out /reports/e1

配置：
    B0 裸提示词（无示例、无约束、无校验/去重）
    B1 +Few-shot 示例
    B2 +约束提示词 + 结构校验 + 去重（当前生产配置）
    B3 B2 + 知识点覆盖（把 ref_kps 传给模型并要求标注 kp）

指标：
    structural_rate  结构合法率（Pydantic 校验 + 规则门控通过比例）
    diversity        题目多样性 = 1 - 题干两两相似度均值
    kp_coverage      知识点覆盖率（题目 kp 标注覆盖 ref_kps 的比例）
    groundedness     接地性（LLM judge，1-5 归一化到 0-1）
    distractor       干扰项质量（LLM judge）
    unambiguity      无歧义性（LLM judge）
"""
import argparse
import csv
import difflib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm import _get_llm_client, _deduplicate_questions
from prompt import build_prompt, _build_example
from quality import check_question
from schemas import QuizOutput, QuestionItem

CONFIGS = ["B0", "B1", "B2", "B3"]


def bare_prompt(content: str, count: int, fewshot: bool) -> str:
    example = _build_example() if fewshot else ""
    return f"""请根据下面的笔记生成 {count} 道单项选择题。
{example}
只输出 JSON，格式如下：
{{"questions": [{{"stem": "题干", "options": ["选项1", "选项2", "选项3", "选项4"], "answer": "A", "explanation": "解析", "kp": "知识点"}}]}}

<note>
{content}
</note>"""


def prompt_for(config: str, content: str, count: int, ref_kps: list) -> str:
    if config == "B0":
        return bare_prompt(content, count, fewshot=False)
    if config == "B1":
        return bare_prompt(content, count, fewshot=True)
    if config == "B2":
        return build_prompt(content, count)
    if config == "B3":
        return build_prompt(content, count, knowledge_points=ref_kps)
    raise ValueError(f"未知配置: {config}")


def generate(config: str, content: str, count: int, ref_kps: list):
    """返回 (raw_questions, kept_questions)。"""
    parser = JsonOutputParser(pydantic_object=QuizOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个只输出 JSON 的出题助手。\n\n{format_instructions}"),
        ("human", "{input}"),
    ])
    chain = prompt | _get_llm_client() | parser

    text = prompt_for(config, content, count, ref_kps)
    result = chain.invoke({
        "input": text,
        "format_instructions": parser.get_format_instructions(),
    })
    raw = result.get("questions", [])

    structurally_valid = []
    for q in raw:
        try:
            QuestionItem(**q)
            if check_question(q) == []:
                structurally_valid.append(q)
        except Exception:
            continue

    kept = structurally_valid
    if config in ("B2", "B3"):
        kept = _deduplicate_questions(kept)
    return raw, kept, len(structurally_valid)


JUDGE_PROMPT = """你是严格的题目质量评审。给定原文和一组选择题，请为每道题打分（1-5，5 最好）：
- groundedness：正确答案与解析能否由原文支持
- distractor：干扰项是否"合理但错误"、有迷惑性
- unambiguity：是否只有一个正确答案、表述无歧义

只输出 JSON，不要输出任何其他内容：
{{"scores": [{{"index": 0, "groundedness": 4, "distractor": 3, "unambiguity": 5}}]}}

<source>
{source}
</source>

<questions>
{questions}
</questions>"""


def judge(content: str, questions: list) -> list:
    if not questions:
        return []
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严格的题目质量评审，只输出 JSON。"),
        ("human", JUDGE_PROMPT),
    ])
    chain = prompt | _get_llm_client() | parser
    result = chain.invoke({
        "source": content,
        "questions": json.dumps(questions, ensure_ascii=False),
    })
    return result.get("scores", [])


def diversity(questions: list) -> float:
    stems = [(q.get("stem") or "").strip() for q in questions]
    stems = [s for s in stems if s]
    if len(stems) < 2:
        return 1.0
    sims = []
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            sims.append(difflib.SequenceMatcher(None, stems[i], stems[j]).ratio())
    return 1.0 - (sum(sims) / len(sims))


def kp_coverage(questions: list, ref_kps: list) -> float:
    if not ref_kps:
        return 0.0
    labels = " ".join((q.get("kp") or "") for q in questions)
    hit = sum(1 for kp in ref_kps if kp and kp in labels)
    return hit / len(ref_kps)


def normalize_score(score, default=3.0) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(1.0, (value - 1.0) / 4.0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/dataset.json")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--configs", default="B0,B1,B2,B3")
    parser.add_argument("--out", default="/reports/e1")
    parser.add_argument("--no-judge", action="store_true", help="跳过 LLM judge（省钱/快速试跑）")
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as f:
        dataset = json.load(f)[: args.limit]

    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    os.makedirs(args.out, exist_ok=True)

    question_rows = []
    summary = {c: [] for c in configs}

    for config in configs:
        for case in dataset:
            source = case["content"]
            ref_kps = case.get("ref_kps", [])
            try:
                raw, kept, structural_ok = generate(config, source, args.count, ref_kps)
            except Exception as e:
                print(f"[{config}/{case['id']}] 生成失败: {e}")
                continue

            scores = [] if args.no_judge else judge(source, kept)
            score_by_index = {int(s.get("index", i)): s for i, s in enumerate(scores)}

            for i, q in enumerate(kept):
                s = score_by_index.get(i, {})
                question_rows.append({
                    "config": config,
                    "note_id": case["id"],
                    "index": i,
                    "stem": q.get("stem", ""),
                    "kp": q.get("kp", ""),
                    "groundedness": normalize_score(s.get("groundedness")) if s else "",
                    "distractor": normalize_score(s.get("distractor")) if s else "",
                    "unambiguity": normalize_score(s.get("unambiguity")) if s else "",
                })

            structural_rate = (structural_ok / len(raw)) if raw else 0.0
            diversity_score = diversity(kept)
            kp_cov = kp_coverage(kept, ref_kps)
            g = [normalize_score(s.get("groundedness")) for s in scores] or [0.0]
            d = [normalize_score(s.get("distractor")) for s in scores] or [0.0]
            u = [normalize_score(s.get("unambiguity")) for s in scores] or [0.0]

            summary[config].append({
                "note_id": case["id"],
                "n_raw": len(raw),
                "n_kept": len(kept),
                "structural_rate": structural_rate,
                "diversity": diversity_score,
                "kp_coverage": kp_cov,
                "groundedness": sum(g) / len(g),
                "distractor": sum(d) / len(d),
                "unambiguity": sum(u) / len(u),
            })
            print(f"[{config}/{case['id']}] raw={len(raw)} kept={len(kept)} "
                  f"struct={structural_rate:.2f} div={diversity_score:.2f} kp={kp_cov:.2f}")
            time.sleep(1)

    q_path = os.path.join(args.out, "e1_questions.csv")
    with open(q_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(question_rows[0].keys()) if question_rows else ["config"])
        writer.writeheader()
        writer.writerows(question_rows)

    def avg(rows, key):
        return sum(r[key] for r in rows) / len(rows) if rows else 0.0

    lines = [
        "# E1 消融实验：题目质量对比",
        "",
        f"- 数据集：{args.dataset}（前 {len(dataset)} 篇）",
        f"- 每篇生成题数：{args.count}",
        f"- 配置：{', '.join(configs)}",
        "",
        "| 配置 | 题数 | 结构合法率 | 多样性 | 知识点覆盖 | 接地性 | 干扰项 | 无歧义 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for config in configs:
        rows = summary[config]
        if not rows:
            lines.append(f"| {config} | 0 | - | - | - | - | - | - |")
            continue
        lines.append(
            f"| {config} | {sum(r['n_kept'] for r in rows)} | "
            f"{avg(rows, 'structural_rate'):.3f} | {avg(rows, 'diversity'):.3f} | "
            f"{avg(rows, 'kp_coverage'):.3f} | {avg(rows, 'groundedness'):.3f} | "
            f"{avg(rows, 'distractor'):.3f} | {avg(rows, 'unambiguity'):.3f} |"
        )
    lines += ["", f"题目明细：`{q_path}`"]

    report_path = os.path.join(args.out, "e1_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\n已写入：{report_path}")


if __name__ == "__main__":
    main()
