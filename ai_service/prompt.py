MAX_CONTENT_LENGTH = 12000
CHUNK_SIZE = 3000


def split_content(content: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """将长文本按段落边界切分为多个块，避免在句子中间截断"""
    if len(content) <= chunk_size:
        return [content]

    paragraphs = content.split('\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += '\n' + para
            else:
                current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def build_prompt(content: str, count: int, chunk_index: int = 0, total_chunks: int = 1) -> str:
    chunk_hint = ""
    if total_chunks > 1:
        chunk_hint = f"\n注意：这是笔记的第 {chunk_index + 1}/{total_chunks} 部分，请仅基于本部分内容出题，不要与其他部分重复。\n"

    return f"""你是一个专业的出题助手。请根据以下笔记内容，生成 {count} 道单项选择题。{chunk_hint}

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

## 格式要求
- 严格按以下 JSON 格式输出，不要包含任何其他内容（不要用 markdown 代码块包裹，直接输出纯 JSON）
- options 数组中只存选项文本，禁止包含 A. B. C. D. 等前缀标签
- answer 字段只能是 A、B、C、D 单个字母，表示第几个选项是正确答案

[
    {{
        "stem": "题目内容",
        "options": ["选项内容", "选项内容", "选项内容", "选项内容"],
        "answer": "A",
        "explanation": "解析内容"
    }}
]

<note_content>
{content}
</note_content>"""