from notes.models import (
    Notebook, Note, Quiz, Question, KnowledgePoint,
    QuestionKnowledgePoint, UserKPMastery,
)
from notes.mastery import update_mastery
from notes.tests import BaseAPITestCase


class BKTMasteryTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name="BKT", user=self.user)
        self.note = Note.objects.create(
            title="BKT 笔记",
            content_md="# BKT",
            content_plain="这是一段足够长的笔记内容，用于 BKT 测试。" * 3,
            notebook=self.notebook,
            user=self.user,
        )
        self.kp = KnowledgePoint.objects.create(
            user=self.user, notebook=self.notebook, name="进程调度"
        )
        self.quiz = Quiz.objects.create(
            note=self.note, user=self.user, status="completed", question_count=1
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            stem="以下哪种调度算法属于非抢占式？",
            options=["时间片轮转", "多级反馈队列", "先来先服务", "最短剩余时间优先"],
            answer="C",
            explanation="先来先服务不会中途剥夺 CPU。",
        )
        QuestionKnowledgePoint.objects.create(question=self.question, kp=self.kp)

    def test_correct_answer_increases_mastery(self):
        p1 = update_mastery(self.user, self.kp, True)
        p2 = update_mastery(self.user, self.kp, True)
        self.assertGreater(p2, p1)

    def test_wrong_answer_decreases_mastery(self):
        UserKPMastery.objects.create(
            user=self.user, kp=self.kp, p_mastery=0.8
        )
        p1 = update_mastery(self.user, self.kp, False)
        self.assertLess(p1, 0.8)

    def test_attempt_updates_mastery(self):
        resp = self.client.post(
            f"/api/v1/quizzes/{self.quiz.id}/attempt/",
            {"answers": [{"question_id": self.question.id, "selected": "C"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        mastery = UserKPMastery.objects.get(user=self.user, kp=self.kp)
        self.assertEqual(mastery.attempts, 1)
        self.assertEqual(mastery.correct, 1)
        self.assertGreater(mastery.p_mastery, 0.30)

    def test_mastery_api(self):
        update_mastery(self.user, self.kp, True)
        resp = self.client.get("/api/v1/learning/mastery/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mastery"][0]["kp_name"], "进程调度")
