import re

MAX_CONTENT_LENGTH = 12000
CHUNK_SIZE = 3000          # 单块上限
CHUNK_TARGET = 2000        # 目标块大小
CHUNK_OVERLAP = 200        # 块间重叠，避免跨块知识点被截断

_HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s+')
_SENTENCE_END = re.compile(r'(?<=[。！？；.!?;])')


def _split_long_paragraph(text: str, max_len: int) -> list[str]:
    """把超长段落按句子边界切开，避免在句子中间截断。"""
    sentences = [s for s in _SENTENCE_END.split(text) if s]
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_len and current:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks or [text]


def split_content(
    content: str,
    chunk_size: int = CHUNK_SIZE,
    target: int = CHUNK_TARGET,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """按 Markdown 标题/段落做语义分块，块间保留少量重叠。

    相比"每 3000 字硬切"，这样能：
    1) 尽量在标题/段落边界处断开，保持知识点完整；
    2) 超长段落按句子边界切，不在句子中间截断；
    3) 相邻块保留 overlap 字符，避免跨块的知识点被切断。
    """
    content = (content or "").strip()
    if not content:
        return []
    if len(content) <= chunk_size:
        return [content]

    # 1) 逐行收集，标题前加空行，形成天然语义边界
    units: list[str] = []
    for line in content.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if _HEADING_RE.match(line) and units:
            units.append("\n\n" + line)
        else:
            units.append(line)

    # 2) 超长行按句子边界再切
    expanded: list[str] = []
    for unit in units:
        if len(unit) > chunk_size:
            expanded.extend(_split_long_paragraph(unit, target))
        else:
            expanded.append(unit)

    # 3) 合并为目标大小的块，相邻块保留重叠
    chunks: list[str] = []
    current = ""
    for unit in expanded:
        separator = "\n" if current else ""
        if len(current) + len(separator) + len(unit) > target and current:
            # 当前块太短（比如只有一行标题）时，跟这个 unit 合并，避免标题单独成块
            if len(current) < 100:
                current = (current + separator + unit).strip()
                continue
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap > 0 else ""
            current = (tail + "\n" + unit).strip()
        else:
            current = (current + separator + unit).strip()
    if current.strip():
        chunks.append(current.strip())

    return chunks


def _build_example() -> str:
    return """## 标准示例

以下是一段笔记内容和期望的题目输出，请严格模仿其风格、难度分布、干扰项设计和解析质量：

<example_note>
进程是操作系统进行资源分配的基本单位。进程调度算法分为抢占式和非抢占式两大类。
先来先服务（FCFS）是最简单的非抢占式算法，按进程到达顺序分配CPU，但可能导致"护航效应"。
短作业优先（SJF）能最小化平均等待时间，但需要预知作业长度，实际中难以实现。
时间片轮转（RR）是抢占式算法，每个进程分配固定时间片，适合分时系统，但时间片太小会导致频繁上下文切换。
多级反馈队列综合了多种策略，新进程进入最高优先级队列，用完时间片后降级，兼顾了响应时间和吞吐量。
</example_note>

<example_output>
{
    "questions": [
        {
            "stem": "以下哪种调度算法属于非抢占式？",
            "options": [
                "时间片轮转（RR）",
                "多级反馈队列",
                "先来先服务（FCFS）",
                "最短剩余时间优先（SRTF）"
            ],
            "answer": "C",
            "explanation": "先来先服务（FCFS）是非抢占式算法，一旦进程获得CPU就会一直运行到完成，不会被中途剥夺。A选项时间片轮转会在时间片用完时强制切换，属于抢占式；B选项多级反馈队列也涉及抢占；D选项SRTF是SJF的抢占式版本。"
        },
        {
            "stem": "某系统采用时间片轮转调度，管理员将时间片从 100ms 调整为 10ms，最可能导致的后果是？",
            "options": [
                "平均等待时间显著降低",
                "CPU利用率大幅提升",
                "上下文切换开销增加，系统吞吐量下降",
                "进程饥饿现象加剧"
            ],
            "answer": "C",
            "explanation": "时间片越小，单位时间内的上下文切换次数越多。每次切换都需要保存和恢复进程上下文，消耗CPU时间。当时间片从100ms降到10ms，切换频率变为原来的10倍，切换开销显著增加，导致实际用于执行进程的CPU比例下降，吞吐量随之降低。A选项错误，因为频繁切换反而可能增加等待时间；B选项错误，切换开销会降低有效利用率；D选项描述的是优先级调度中的饥饿问题，与时间片轮转无关。"
        }
    ]
}
</example_output>

请基于以上示例的风格，为下方笔记内容生成题目。"""


def build_prompt(
    content: str,
    count: int,
    chunk_index: int = 0,
    total_chunks: int = 1,
    knowledge_points: list[str] | None = None,
) -> str:
    chunk_hint = ""
    if total_chunks > 1:
        chunk_hint = f"\n注意：这是笔记的第 {chunk_index + 1}/{total_chunks} 部分，请仅基于本部分内容出题，不要与其他部分重复。\n"

    kp_hint = ""
    if knowledge_points:
        kp_list = "、".join(knowledge_points)
        kp_hint = (
            f"\n## 知识点标注\n"
            f"本题库包含以下知识点：{kp_list}。\n"
            f"请为每道题标注它考察的知识点，写入 kp 字段；优先使用上面列表中的名称。\n"
        )

    return f"""你是一个专业的出题助手。请根据以下笔记内容，生成 {count} 道单项选择题。{chunk_hint}{kp_hint}

## 出题原则

### 1. 难度分层
- 简单题：考察基础事实的识记，答案可直接从原文定位
- 中等题：考察概念的理解与辨析，需要一定的推理判断
- 困难题：考察知识的综合应用与分析，需要跨知识点联想
- 请合理分配三种难度，避免全部集中在同一难度

### 2. 知识点覆盖
- 先通读笔记，识别出其中 {count} 个关键知识点
- 每道题围绕不同的知识点展开，避免多道题考察同一内容

### 3. 干扰项质量
- 错误选项必须看起来"合理但错误"，对未掌握知识的学习者具有迷惑性
- 四个选项的长度、表述风格、具体程度应保持一致
- 禁止使用"以上都对"、"以上都不对"、"A和B都对"等万能选项
- 禁止选项之间存在包含关系（如 A="操作系统"，B="操作系统中的进程调度"）

### 4. 题目多样性
- 避免所有题目都是"以下哪项正确/错误"的单一形式
- 可交替使用"最可能的原因是"、"最合适的解释是"、"体现了什么"等问法

### 5. 解析质量
- 先说明正确答案为什么对，再简要指出关键错误选项的陷阱所在
- 禁止使用"根据原文可知"、"显而易见"等空洞表述

{_build_example()}

## 格式要求
- 严格按以下 JSON 格式输出，不要包含任何其他内容（不要用 markdown 代码块包裹，直接输出纯 JSON）
- options 数组中只存选项文本，禁止包含 A. B. C. D. 等前缀标签
- answer 字段只能是 A、B、C、D 单个字母，表示第几个选项是正确答案
- kp 字段填写该题考察的知识点名称

{{
    "questions": [
        {{
            "stem": "题目内容",
            "options": ["选项内容", "选项内容", "选项内容", "选项内容"],
            "answer": "A",
            "explanation": "解析内容",
            "kp": "该题考察的知识点"
        }}
    ]
}}

<note_content>
{content}
</note_content>"""


def build_kp_prompt(content: str, max_points: int = 8) -> str:
    return f"""你是一个知识点抽取助手。请从下面的笔记中抽取最多 {max_points} 个核心知识点。

## 要求
- 每个知识点是一个可以独立考察的概念、原理或技能
- name 简短（不超过 20 字），不要带编号
- description 用一句话说明该知识点
- 去重，不要把同一个知识点拆成多条
- 只输出 JSON，不要输出任何其他内容

## 输出格式
{{
  "knowledge_points": [
    {{"name": "知识点名称", "description": "一句话说明"}}
  ]
}}

<note_content>
{content}
</note_content>"""