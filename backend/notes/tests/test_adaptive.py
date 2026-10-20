from notes.models import (
    Notebook, Note, Quiz, Question, KnowledgePoint,
    QuestionKnowledgePoint, UserKPMastery,
)
from notes.tests import BaseAPITestCase


class AdaptiveSelectionTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name="自适应", user=self.user)
        self.note = Note.objects.create(
            title="自适应笔记",
            content_md="# 自适应",
            content_plain="这是一段足够长的笔记内容，用于自适应测试。" * 3,
            notebook=self.notebook,
            user=self.user,
        )
        self.quiz = Quiz.objects.create(
            note=self.note, user=self.user, status="completed", question_count=2
        )
        self.kp_weak = KnowledgePoint.objects.create(
            user=self.user, notebook=self.notebook, name="薄弱知识点"
        )
        self.kp_strong = KnowledgePoint.objects.create(
            user=self.user, notebook=self.notebook, name="已掌握知识点"
        )
        UserKPMastery.objects.create(user=self.user, kp=self.kp_weak, p_mastery=0.5)
        UserKPMastery.objects.create(user=self.user, kp=self.kp_strong, p_mastery=0.95)

        self.q_weak = self._make_question("薄弱知识点的题目", self.kp_weak)
        self.q_strong = self._make_question("已掌握知识点的题目", self.kp_strong)

    def _make_question(self, stem, kp):
        q = Question.objects.create(
            quiz=self.quiz, stem=stem,
            options=["甲", "乙", "丙", "丁"], answer="A", explanation="解析",
        )
        QuestionKnowledgePoint.objects.create(question=q, kp=kp)
        return q

    def test_adaptive_prefers_weak_kp(self):
        resp = self.client.post(
            "/api/v1/quizzes/adaptive/",
            {"note_id": self.note.id, "count": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        # 掌握度接近 0.5 的"薄弱知识点"应排在最前
        self.assertEqual(resp.data["questions"][0]["stem"], "薄弱知识点的题目")

    def test_adaptive_returns_404_when_no_questions(self):
        empty_note = Note.objects.create(
            title="空笔记", content_md="x", content_plain="x" * 60,
            notebook=self.notebook, user=self.user,
        )
        resp = self.client.post(
            "/api/v1/quizzes/adaptive/",
            {"note_id": empty_note.id, "count": 5},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
