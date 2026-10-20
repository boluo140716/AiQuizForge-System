from django.db import connection
from django.test.utils import CaptureQueriesContext

from notes.models import Notebook, Note, Quiz, QuizAttempt
from notes.tests import BaseAPITestCase


class QueryCountTests(BaseAPITestCase):
    """回归测试：列表接口的查询数不应随数据量增长（防 N+1）。"""

    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='主笔记本', user=self.user)
        self.note = Note.objects.create(
            title='笔记', content_md='x', content_plain='x' * 60,
            notebook=self.notebook, user=self.user,
        )
        for _ in range(3):
            quiz = Quiz.objects.create(
                note=self.note, user=self.user, status='completed', question_count=1
            )
            QuizAttempt.objects.create(
                quiz=quiz, user=self.user, score=1, total=1, correct_rate=1.0
            )

    def _count_queries(self, url):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx)

    def test_quiz_list_queries_do_not_grow(self):
        before = self._count_queries('/api/v1/quizzes/')
        for _ in range(3):
            quiz = Quiz.objects.create(
                note=self.note, user=self.user, status='completed', question_count=1
            )
            QuizAttempt.objects.create(
                quiz=quiz, user=self.user, score=1, total=1, correct_rate=1.0
            )
        after = self._count_queries('/api/v1/quizzes/')
        self.assertEqual(before, after)

    def test_notebook_list_queries_do_not_grow(self):
        before = self._count_queries('/api/v1/notebooks/')
        for i in range(3):
            notebook = Notebook.objects.create(name=f'附加{i}', user=self.user)
            Note.objects.create(
                title=f'笔记{i}', content_md='x', content_plain='x' * 60,
                notebook=notebook, user=self.user,
            )
        after = self._count_queries('/api/v1/notebooks/')
        self.assertEqual(before, after)
