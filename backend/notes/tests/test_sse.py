from rest_framework_simplejwt.tokens import RefreshToken

from notes.models import Notebook, Note, Quiz
from notes.tests import BaseAPITestCase


class QuizStreamTests(BaseAPITestCase):
    def test_stream_requires_valid_token(self):
        """没有 token 应返回 401。"""
        resp = self.client.get('/api/v1/quizzes/1/stream/')
        self.assertEqual(resp.status_code, 401)

    def test_stream_completed_quiz_returns_event(self):
        """已完成的测验应能建立 SSE 连接并收到至少一条 data 事件。"""
        notebook = Notebook.objects.create(name='SSE测试', user=self.user)
        note = Note.objects.create(
            title='SSE',
            content_md='# SSE',
            content_plain='这是一段用于测试的笔记内容，长度足够生成测验。' * 3,
            notebook=notebook,
            user=self.user,
        )
        quiz = Quiz.objects.create(
            note=note, user=self.user, status='completed', question_count=3
        )
        token = str(RefreshToken.for_user(self.user).access_token)

        resp = self.client.get(f'/api/v1/quizzes/{quiz.id}/stream/?token={token}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/event-stream', resp['Content-Type'])

        first_chunk = next(iter(resp.streaming_content)).decode()
        self.assertIn('data:', first_chunk)
