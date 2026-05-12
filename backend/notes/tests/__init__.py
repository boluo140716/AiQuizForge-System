from rest_framework.test import APITestCase,APIClient
from django.contrib.auth import get_user_model   # 获取用户模型
User = get_user_model()   

class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='testuser',password='testpass123',email='test@example.com')
        self.other_user=User.objects.create_user(username='otheruser',password='otherpass123',email='other@example.com')
        self.client=APIClient()
        #登录认证并获取JWT token
        response=self.client.post('/api/v1/auth/login/',{'username':'testuser','password':'testpass123'})
        self.token=response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
