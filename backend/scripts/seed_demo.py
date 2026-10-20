import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from notes.models import (
    Notebook, Note, KnowledgePoint, UserKPMastery,
    Quiz, Question, QuizAttempt,
)

U = get_user_model()
user, _ = U.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
user.set_password("demo12345")
user.save()

nb, _ = Notebook.objects.get_or_create(name="操作系统", user=user)

notes_data = [
    ("进程与线程", "# 进程与线程\n\n进程是资源分配的基本单位，线程是 CPU 调度的基本单位。"),
    ("TCP 三次握手", "# TCP 三次握手\n\n客户端发送 SYN，服务端回复 SYN+ACK，客户端再发送 ACK。"),
    ("数据库事务", "# 数据库事务\n\n事务具有 ACID 特性，InnoDB 默认使用可重复读隔离级别。"),
    ("死锁的四个条件", "# 死锁\n\n互斥、占有并等待、不可抢占、循环等待。"),
]
notes = []
for title, md in notes_data:
    note, _ = Note.objects.get_or_create(
        title=title, notebook=nb, user=user,
        defaults={"content_md": md, "content_plain": md},
    )
    notes.append(note)

kp_levels = {
    "进程与线程": 0.72,
    "进程调度算法": 0.48,
    "TCP三次握手": 0.35,
    "拥塞控制": 0.81,
    "事务与ACID": 0.55,
}
for name, level in kp_levels.items():
    kp, _ = KnowledgePoint.objects.get_or_create(user=user, notebook=nb, name=name)
    UserKPMastery.objects.update_or_create(
        user=user, kp=kp,
        defaults={"p_mastery": level, "attempts": 6, "correct": round(level * 6)},
    )

quiz, _ = Quiz.objects.get_or_create(
    note=notes[0], user=user,
    defaults={"status": "completed", "question_count": 3},
)
quiz.status = "completed"
quiz.question_count = 3
quiz.save(update_fields=["status", "question_count"])

quiz.questions.all().delete()
demo_questions = [
    {
        "stem": "进程是资源分配的基本单位，线程是什么的基本单位？",
        "options": ["资源分配", "CPU 调度", "内存管理", "文件管理"],
        "answer": "B",
        "explanation": "线程是 CPU 调度和执行的基本单位；进程拥有独立的地址空间，是资源分配的基本单位。",
    },
    {
        "stem": "下列哪种进程调度算法最适合交互式分时系统？",
        "options": ["先来先服务（FCFS）", "短作业优先（SJF）", "时间片轮转（RR）", "非抢占式优先级调度"],
        "answer": "C",
        "explanation": "时间片轮转按固定时间片轮流分配 CPU，响应快且公平，适合分时系统。",
    },
    {
        "stem": "死锁的四个必要条件中，哪一个可以通过“按编号顺序申请锁”来破坏？",
        "options": ["互斥", "占有并等待", "不可抢占", "循环等待"],
        "answer": "D",
        "explanation": "所有进程按同一顺序申请锁时，等待关系不会形成环，从而破坏循环等待条件。",
    },
]
for item in demo_questions:
    Question.objects.create(quiz=quiz, **item)

QuizAttempt.objects.filter(user=user, quiz=quiz).delete()
for rate in (0.33, 0.67, 0.67, 1.0, 0.67):
    QuizAttempt.objects.create(
        quiz=quiz, user=user, score=round(rate * 3), total=3,
        correct_rate=rate, answers_detail=[],
    )

print("demo seeded: username=demo password=demo12345")
