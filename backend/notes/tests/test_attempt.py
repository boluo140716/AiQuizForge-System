import json
from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note, Quiz, Question

class AttemptTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='学习', user=self.user)
        self.note = Note.objects.create(
            title='测试笔记', content_md='内容',
            notebook=self.notebook, user=self.user
        )
        # 创建一个已完成的测验
        self.quiz = Quiz.objects.create(
            note=self.note, user=self.user, status='completed', question_count=2
        )
        # 创建题目
        self.q1 = Question.objects.create(
            quiz=self.quiz, stem="1+1=?", options=["A: 1", "B: 2", "C: 3", "D: 4"],
            answer="B", explanation="数学基础"
        )
        self.q2 = Question.objects.create(
            quiz=self.quiz, stem="2+2=?", options=["A: 1", "B: 2", "C: 3", "D: 4"],
            answer="D", explanation="也是基础"
        )

    def test_attempt_score_calculation(self):
        """提交部分正确答案，验证判分与错题收录"""
        response = self.client.post(
            f'/api/v1/quizzes/{self.quiz.id}/attempt/',
            json.dumps({
                'answers': [
                    {'question_id': self.q1.id, 'selected': 'B'},  # 正确
                    {'question_id': self.q2.id, 'selected': 'A'}   # 错误
                ]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['score'], 1)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['correct_rate'], 0.5)
        # 验证错题本
        from notes.models import WrongQuestion
        self.assertEqual(WrongQuestion.objects.filter(user=self.user).count(), 1)
        wrong = WrongQuestion.objects.first()
        self.assertEqual(wrong.question, self.q2)
        self.assertEqual(wrong.user_answer, 'A')
        self.assertEqual(wrong.wrong_count, 1)

    def test_attempt_with_invalid_quiz_status(self):
        """对未完成的测验提交答案应返回400"""
        self.quiz.status = 'processing'
        self.quiz.save()
        response = self.client.post(
            f'/api/v1/quizzes/{self.quiz.id}/attempt/',
            {'answers': []}
        )
        self.assertEqual(response.status_code, 400)