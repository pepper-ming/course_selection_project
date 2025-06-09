from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthenticationAPITestCase(TestCase):
    """測試認證相關 API"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 建立測試使用者
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            name='測試使用者',
            role='student',
            email='test@example.com'
        )
    
    def test_login_success(self):
        """測試成功登入"""
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # 檢查回應內容
        self.assertIn('user', response_data)
        self.assertIn('message', response_data)
        self.assertEqual(response_data['message'], '登入成功')
        
        # 檢查使用者資訊
        user_data = response_data['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['name'], '測試使用者')
        self.assertEqual(user_data['role'], 'student')
        
        # 確認 session 已建立
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_login_invalid_credentials(self):
        """測試無效憑證登入"""
        url = reverse('login')
        
        # 錯誤密碼
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()
        
        self.assertIn('detail', response_data)
        self.assertEqual(response_data['detail'], '登入失敗')
        self.assertIn('errors', response_data)
    
    def test_login_nonexistent_user(self):
        """測試不存在的使用者登入"""
        url = reverse('login')
        data = {
            'username': 'nonexistent',
            'password': 'somepassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_missing_fields(self):
        """測試缺少必要欄位"""
        url = reverse('login')
        
        # 缺少密碼
        data = {'username': 'testuser'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 缺少使用者名稱
        data = {'password': 'testpass123'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout_success(self):
        """測試成功登出"""
        # 先登入
        self.client.force_authenticate(user=self.test_user)
        
        url = reverse('logout')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertEqual(response_data['message'], '登出成功')
        
        # 確認 session 已清除
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_logout_requires_auth(self):
        """測試登出需要已登入"""
        url = reverse('logout')
        response = self.client.post(url)
        
        # 可能返回 401 或 403，取決於認證設定
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_current_user_success(self):
        """測試取得當前使用者資訊"""
        self.client.force_authenticate(user=self.test_user)
        
        url = reverse('current-user')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['name'], '測試使用者')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['role'], 'student')
        self.assertEqual(data['role_display'], '學生')
    
    def test_current_user_requires_auth(self):
        """測試取得當前使用者需要登入"""
        url = reverse('current-user')
        response = self.client.get(url)
        
        # 可能返回 401 或 403
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_register_success(self):
        """測試成功註冊"""
        url = reverse('register')
        data = {
            'username': 'newstudent',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'name': '新學生',
            'email': 'new@example.com',
            'role': 'student'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        
        self.assertEqual(response_data['message'], '註冊成功')
        self.assertIn('user', response_data)
        
        # 確認使用者已建立
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.name, '新學生')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(user.check_password('newpass123'))
    
    def test_register_password_mismatch(self):
        """測試註冊時密碼不符"""
        url = reverse('register')
        data = {
            'username': 'newstudent',
            'password': 'newpass123',
            'password_confirm': 'differentpass',
            'name': '新學生'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()
        self.assertIn('密碼與確認密碼不符', str(errors))
    
    def test_register_duplicate_username(self):
        """測試註冊重複的使用者名稱"""
        url = reverse('register')
        data = {
            'username': 'testuser',  # 已存在的使用者名稱
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'name': '另一個使用者'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_short_password(self):
        """測試密碼太短"""
        url = reverse('register')
        data = {
            'username': 'newstudent',
            'password': 'short',  # 少於8個字元
            'password_confirm': 'short',
            'name': '新學生'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)