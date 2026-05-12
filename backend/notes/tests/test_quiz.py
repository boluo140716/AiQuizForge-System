from unittest.mock import patch
from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note

class QuizGenerationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='学习', user=self.user)
        self.note = Note.objects.create(
            title='Python基础', content_md='# 列表与元组\n列表可变，元组不可变。',
            notebook=self.notebook, user=self.user
        )

    @patch('notes.task.generate_quiz.delay')   # 模拟异步任务（注意是 task.py 不是 tasks.py）
    def test_generate_quiz_success(self, mock_delay):
        """正常生成测验，返回202并创建Quiz记录"""
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
        # 确认异步任务被调用了一次
        mock_delay.assert_called_once_with(quiz_id)

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