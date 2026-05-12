import json
from notes.tests import BaseAPITestCase
from notes.models import Notebook, Note


class NotebookTests(BaseAPITestCase):
    def test_create_notebook(self):
        # 测试创建笔记本接口
        response=self.client.post('/api/v1/notebooks/',{'name':'学习笔记'})
        self.assertEqual(response.status_code,201)
        self.assertEqual(Notebook.objects.count(),1)
        self.assertEqual(Notebook.objects.first().user,self.user)


    def test_list_only_own_notebooks(self):
        # 测试列出用户自己的笔记本接口
        Notebook.objects.create(name='别人的笔记本',user=self.other_user)
        response=self.client.get('/api/v1/notebooks/')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results),0)

class NoteTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.notebook = Notebook.objects.create(name='测试本', user=self.user)

    def test_create_note_auto_plain_text(self):
        """创建笔记时自动提取纯文本"""
        response = self.client.post(
            '/api/v1/notes/',
            json.dumps({
                'title': '测试笔记',
                'content_md': '# 标题\n内容段落',
                'notebook': self.notebook.id,
                'tags': ['test']
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        note = Note.objects.first()
        self.assertIn('内容段落', note.content_plain)
        self.assertNotIn('#', note.content_plain)

    def test_other_user_cannot_see_my_note(self):
        """另一个用户不能看到我的笔记"""
        note = Note.objects.create(
            title='我的笔记', content_md='...',
            notebook=self.notebook, user=self.user
        )
        # 切换客户端为other_user
        other_client = self.client_class()
        response = other_client.post('/api/v1/auth/login/', {
            'username': 'otheruser', 'password': 'otherpass123'
        })
        token = response.data['access']
        other_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        # 尝试获取不是我创建的笔记详情，应返回404
        response = other_client.get(f'/api/v1/notes/{note.id}/')
        self.assertEqual(response.status_code, 404)