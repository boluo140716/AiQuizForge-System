from django.core.files.uploadedfile import SimpleUploadedFile

from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note, Quiz, Question


class InteropTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='导入目标', user=self.user)

    def test_import_markdown_creates_note(self):
        upload = SimpleUploadedFile(
            '线性代数.md',
            '# 矩阵\n矩阵乘法不满足交换律。'.encode('utf-8'),
            content_type='text/markdown',
        )
        response = self.client.post(
            '/api/v1/io/import/',
            {'files': [upload], 'notebook_id': self.notebook.id},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        note = Note.objects.get(user=self.user, title='线性代数')
        self.assertEqual(note.notebook, self.notebook)
        self.assertIn('矩阵乘法', note.content_plain)
        self.assertNotIn('#', note.content_plain)

    def test_import_rejects_unsupported_file(self):
        upload = SimpleUploadedFile('a.pdf', b'%PDF', content_type='application/pdf')
        response = self.client.post(
            '/api/v1/io/import/', {'files': [upload]}, format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 0)
        self.assertEqual(response.data['skipped'], 1)

    def test_import_without_notebook_uses_default(self):
        upload = SimpleUploadedFile(
            '默认本.md', '内容'.encode('utf-8'), content_type='text/markdown'
        )
        response = self.client.post(
            '/api/v1/io/import/', {'files': [upload]}, format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        note = Note.objects.get(user=self.user, title='默认本')
        self.assertEqual(note.notebook.name, '导入笔记')

    def test_export_questions_csv(self):
        quiz = Quiz.objects.create(
            note=None, user=self.user, status='completed', question_count=1
        )
        Question.objects.create(
            quiz=quiz,
            stem='矩阵乘法满足交换律吗？',
            options=['A: 满足', 'B: 不满足', 'C: 有时', 'D: 无关'],
            answer='B',
            explanation='一般不满足',
        )
        response = self.client.get('/api/v1/io/export/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode('utf-8-sig')
        self.assertIn('矩阵乘法满足交换律吗？', body)
        self.assertIn('题干', body)
        self.assertIn('一般不满足', body)

    def test_export_only_contains_own_questions(self):
        other_quiz = Quiz.objects.create(
            note=None, user=self.other_user, status='completed', question_count=1
        )
        Question.objects.create(
            quiz=other_quiz,
            stem='别人的题目',
            options=['A: 1', 'B: 2', 'C: 3', 'D: 4'],
            answer='A',
        )
        response = self.client.get('/api/v1/io/export/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8-sig')
        self.assertNotIn('别人的题目', body)
