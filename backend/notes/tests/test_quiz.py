from unittest.mock import patch
from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note
from notes.utils import md_to_plain_text

class QuizGenerationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='学习', user=self.user)
        md_content = '# 列表与元组\n\n列表是Python中最常用的数据结构之一，可以存储任意类型的数据。\n元组是不可变的序列类型。'
        self.note = Note.objects.create(
            title='Python基础', content_md=md_content,
            content_plain=md_to_plain_text(md_content),
            notebook=self.notebook, user=self.user
        )

    @patch('notes.task.generate_quiz.delay')   # 模拟异步任务（注意是 task.py 不是 tasks.py）
    def test_generate_quiz_success(self, mock_delay):
        """正常生成测验，返回202并创建Quiz记录"""
        mock_delay.return_value.id = 'fake-celery-task-id'
        response = self.client.post(
            f'/api/v1/quizzes/generate/{self.note.id}/',
            {'question_count': 3}
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], 'processing')
        quiz_id = response.data['quiz_id']
        from notes.models import Quiz
        quiz = Quiz.objects.get(id=quiz_id)
        self.assertEqual(quiz.user, self.user)
        self.assertEqual(quiz.note, self.note)
        # 确认异步任务被调用了一次（现在还会额外传 trace_id，故用更宽松的断言）
        mock_delay.assert_called_once()
        called_args, called_kwargs = mock_delay.call_args
        self.assertEqual(called_args[0], quiz_id)
        self.assertIn('trace_id', called_kwargs)

    @patch('notes.task.generate_quiz.delay')
    def test_generate_quiz_idempotent(self, mock_delay):
        """同一个 Idempotency-Key 重复提交，只创建一个测验，第二次返回 duplicated=True"""
        import uuid
        mock_delay.return_value.id = 'fake-celery-task-id'
        key = uuid.uuid4().hex
        headers = {'HTTP_IDEMPOTENCY_KEY': key}

        r1 = self.client.post(
            f'/api/v1/quizzes/generate/{self.note.id}/',
            {'question_count': 3}, **headers
        )
        r2 = self.client.post(
            f'/api/v1/quizzes/generate/{self.note.id}/',
            {'question_count': 3}, **headers
        )

        self.assertEqual(r1.status_code, 202)
        self.assertEqual(r2.status_code, 202)
        self.assertEqual(r1.data['quiz_id'], r2.data['quiz_id'])
        self.assertTrue(r2.data.get('duplicated'))

        from notes.models import Quiz
        self.assertEqual(
            Quiz.objects.filter(user=self.user, idempotency_key=key).count(),
            1,
        )

    def test_generate_quiz_content_too_short(self):
        """笔记内容太短时返回400"""
        short_note = Note.objects.create(
            title='短', content_md='很短',
            notebook=self.notebook, user=self.user
        )
        response = self.client.post(
            f'/api/v1/quizzes/generate/{short_note.id}/',
            {'question_count': 3}
        )
        self.assertEqual(response.status_code, 400)