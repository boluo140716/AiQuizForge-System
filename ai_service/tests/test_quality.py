"""语义分块 + 题目质量门控的单元测试。

运行：python tests/test_quality.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt import split_content          # noqa: E402
from quality import check_question        # noqa: E402


def test_split_short_content():
    assert split_content("很短的一段内容") == ["很短的一段内容"]


def test_split_respects_size():
    content = "# 标题\n" + "这是一句内容。" * 800 + "\n## 二级标题\n" + "更多内容。" * 800
    chunks = split_content(content, chunk_size=1000, target=800, overlap=50)
    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    # 单块不应无限膨胀（允许 chunk_size + overlap 的余量）
    assert all(len(chunk) <= 1000 + 50 + 50 for chunk in chunks)


def test_split_keeps_headings_with_content():
    content = "# 第一部分\n" + "甲" * 900 + "\n# 第二部分\n" + "乙" * 900
    chunks = split_content(content, chunk_size=1000, target=700, overlap=0)
    assert any("第一部分" in c for c in chunks)
    assert any("第二部分" in c for c in chunks)


def test_quality_rejects_duplicate_options():
    q = {
        "stem": "以下哪个选项正确？",
        "options": ["相同选项", "相同选项", "另一个", "再一个"],
        "answer": "A",
        "explanation": "解析内容",
    }
    assert "存在重复选项" in check_question(q)


def test_quality_rejects_banned_option():
    q = {
        "stem": "以下哪个说法正确？",
        "options": ["甲说法", "乙说法", "丙说法", "以上都对"],
        "answer": "A",
        "explanation": "解析内容",
    }
    assert "使用了万能选项" in check_question(q)


def test_quality_rejects_similar_options():
    q = {
        "stem": "以下哪个说法正确？",
        "options": ["进程是资源分配的基本单位", "进程是资源分配的基本单位。", "线程是调度单位", "协程是用户态线程"],
        "answer": "A",
        "explanation": "解析内容",
    }
    assert "选项过于相似" in check_question(q)


def test_quality_accepts_good_question():
    q = {
        "stem": "进程调度中，哪种算法属于非抢占式？",
        "options": ["时间片轮转", "多级反馈队列", "先来先服务", "最短剩余时间优先"],
        "answer": "C",
        "explanation": "先来先服务一旦获得 CPU 就会运行到完成，不会中途剥夺。",
    }
    assert check_question(q) == []


def test_prompt_includes_knowledge_points():
    from prompt import build_prompt
    prompt_text = build_prompt("这是一段用于测试的笔记内容。" * 10, 5,
                               knowledge_points=["进程调度", "死锁"])
    assert "进程调度" in prompt_text and "死锁" in prompt_text
    assert '"kp"' in prompt_text


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
