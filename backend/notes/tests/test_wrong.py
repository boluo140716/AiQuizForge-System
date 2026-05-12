from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note, Quiz, Question, WrongQuestion

class WrongQuestionTests(BaseAPITestCase):
    def setUp(self):  # 设置测试环境
        super().setUp()
        self.notebook = Notebook.objects.create(name='学习', user=self.user)
        self.note = Note.objects.create(
            title='测试笔记', content_md='...',
            notebook=self.notebook, user=self.user
        )
        quiz = Quiz.objects.create(note=self.note, user=self.user, status='completed', question_count=1)
        self.q = Question.objects.create(
            quiz=quiz, stem="错误题", options=["A","B","C","D"], answer="A"
        )
        # 创建一条错题记录
        WrongQuestion.objects.create(
            user=self.user, question=self.q, quiz=quiz,
            user_answer='B', wrong_count=1
        )

    def test_wrong_list(self):
        """获取错题列表"""
        response = self.client.get('/api/v1/wrong-questions/list/')
        self.assertEqual(response.status_code, 200)
        # 处理分页响应，数据在 results 中
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['question_stem'], '错误题')

    def test_remove_wrong(self):
        """移除错题"""
        wrong_id = WrongQuestion.objects.first().id
        response = self.client.delete(f'/api/v1/wrong-questions/{wrong_id}/remove/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(WrongQuestion.objects.count(), 0)