from notes.tests import BaseAPITestCase
from django.urls import reverse  # 用于生成URL

class AuthTests(BaseAPITestCase):
    def test_register_user(self):
        # 测试注册用户接口
        url='/api/v1/auth/register/'
        response=self.client.post(url,{'username':'newuser','password':'newpass123','password2':'newpass123','email':'new@example.com'})
        self.assertEqual(response.status_code,201) 
        self.assertIn('username',response.data) # 检查响应数据是否包含用户名

    def test_login_jwt(self):
        # 测试JWT登录接口
        url='/api/v1/auth/login/'
        response=self.client.post(url,{'username':'testuser','password':'testpass123'})
        self.assertEqual(response.status_code,200) 
        self.assertIn('access',response.data) # 检查响应数据是否包含access token
        self.assertIn('refresh',response.data) # 检查响应数据是否包含refresh token

    def test_get_me(self):
        # 测试获取当前用户信息接口
        url='/api/v1/auth/me/'
        response=self.client.get(url)
        self.assertEqual(response.status_code,200) 
        self.assertEqual(response.data['username'],'testuser') # 检查响应数据是否包含用户名
