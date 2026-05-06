def build_prompt(content: str, count: int) -> str:
    return f"""
    你是一个专业的出题助手。请根据以下笔记内容，生成 {count} 道单项选择题。
    要求：
    1. 每道题必须有 4 个选项（A/B/C/D），并标明正确答案。
    2. 选项不能完全照搬原文，需要提炼理解。
    3. 为每道题写一句简短的解析，解释为什么正确。
    4. 严格按以下 JSON 格式输出，不要包含任何其他内容（不要用 markdown 代码块包裹，直接输出纯 JSON）：

    [
    {{
        "stem": "题目内容",
        "options": ["A: ...", "B: ...", "C: ...", "D: ..."],
        "answer": "A",
        "explanation": "解析内容"
    }}
    ]

    笔记内容：
    {content}
            """
