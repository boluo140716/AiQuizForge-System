from datetime import timedelta

from django.utils import timezone

from notes.models import (
    Notebook, Note, Quiz, Question, ReviewSchedule,
)
from notes.srs import sm2_next
from notes.tests import BaseAPITestCase


class SM2Tests(BaseAPITestCase):
    def test_correct_sequence_intervals(self):
        ef, interval, reps, lapses = 2.5, 0, 0, 0
        ef, interval, reps, lapses = sm2_next(ef, interval, reps, lapses, 4)
        self.assertEqual((interval, reps), (1, 1))
        ef, interval, reps, lapses = sm2_next(ef, interval, reps, lapses, 4)
        self.assertEqual((interval, reps), (6, 2))
        ef, interval, reps, lapses = sm2_next(ef, interval, reps, lapses, 4)
        self.assertGreaterEqual(interval, 6)
        self.assertEqual(reps, 3)

    def test_wrong_resets(self):
        ef, interval, reps, lapses = sm2_next(2.5, 10, 5, 0, 2)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 0)
        self.assertEqual(lapses, 1)

    def test_ef_clamped(self):
        ef, _, _, _ = sm2_next(1.3, 1, 1, 0, 0)
        self.assertGreaterEqual(ef, 1.3)


class ReviewAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name="复习", user=self.user)
        self.note = Note.objects.create(
            title="复习笔记",
            content_md="# 复习",
            content_plain="这是一段足够长的笔记内容，用于复习测试。" * 3,
            notebook=self.notebook,
            user=self.user,
        )
        self.quiz = Quiz.objects.create(
            note=self.note, user=self.user, status="completed", question_count=1
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            stem="复习题",
            options=["甲", "乙", "丙", "丁"],
            answer="A",
            explanation="解析",
        )
        ReviewSchedule.objects.create(
            user=self.user,
            question=self.question,
            due_at=timezone.now() - timedelta(days=1),
        )

    def test_due_list(self):
        resp = self.client.get("/api/v1/learning/review/due/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["due_count"], 1)
        self.assertEqual(resp.data["items"][0]["stem"], "复习题")

    def test_review_practice_creates_quiz(self):
        resp = self.client.post(
            "/api/v1/learning/review/practice/", {"count": 10}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        from notes.models import Question as Q
        copy = Q.objects.get(quiz_id=resp.data["practice_quiz_id"])
        self.assertEqual(copy.origin_id, self.question.id)

    def test_attempt_updates_schedule(self):
        resp = self.client.post(
            f"/api/v1/quizzes/{self.quiz.id}/attempt/",
            {"answers": [{"question_id": self.question.id, "selected": "A"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        after = ReviewSchedule.objects.get(user=self.user, question=self.question)
        self.assertEqual(after.repetitions, 1)
        self.assertGreater(after.due_at, timezone.now())
