from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import time
import json

from courses.models import Course, Enrollment, CourseTimeSlot
from courses.services import MAX_COURSE_LIMIT, MIN_COURSE_LIMIT

User = get_user_model()


class CourseAPITestCase(TestCase):
    """測試課程查詢 API"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 建立測試使用者
        self.student = User.objects.create_user(
            username='student001',
            password='password123',
            name='測試學生',
            role='student'
        )
        
        # 建立測試課程
        self.course1 = Course.objects.create(
            name='資料結構',
            course_code='CS101',
            type='必修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        
        self.course2 = Course.objects.create(
            name='演算法',
            course_code='CS102',
            type='必修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        
        self.course3 = Course.objects.create(
            name='機器學習導論',
            course_code='CS301',
            type='選修',
            capacity=40,
            credit=3,
            semester='113上'
        )
        
        # 建立課程時間
        CourseTimeSlot.objects.create(
            course=self.course1,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(12, 0),
            location='資訊館101'
        )
    
    def test_list_courses_no_auth(self):
        """測試未登入也能查詢課程列表"""
        url = reverse('course-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # 檢查回應格式
        self.assertIn('count', data)
        self.assertIn('results', data)
        self.assertEqual(data['count'], 3)
        self.assertEqual(len(data['results']), 3)
    
    def test_list_courses_with_search(self):
        """測試課程搜尋功能"""
        url = reverse('course-list')
        response = self.client.get(url, {'search': '資料'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['name'], '資料結構')
    
    def test_list_courses_with_type_filter(self):
        """測試課程類型篩選"""
        url = reverse('course-list')
        
        # 篩選必修課程
        response = self.client.get(url, {'type': '必修'})
        data = response.json()
        self.assertEqual(data['count'], 2)
        
        # 篩選選修課程
        response = self.client.get(url, {'type': '選修'})
        data = response.json()
        self.assertEqual(data['count'], 1)
    
    def test_list_courses_with_semester_filter(self):
        """測試學期篩選"""
        # 建立不同學期的課程
        Course.objects.create(
            name='深度學習',
            course_code='CS401',
            type='選修',
            capacity=35,
            credit=3,
            semester='113下'
        )
        
        url = reverse('course-list')
        response = self.client.get(url, {'semester': '113上'})
        data = response.json()
        
        self.assertEqual(data['count'], 3)
    
    def test_retrieve_course(self):
        """測試取得單一課程詳情"""
        url = reverse('course-detail', kwargs={'pk': self.course1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['name'], '資料結構')
        self.assertEqual(data['course_code'], 'CS101')
        self.assertIn('timeslots', data)
        self.assertEqual(len(data['timeslots']), 1)
    
    def test_course_enrollment_counts(self):
        """測試課程選課人數計算"""
        # 登入並選課
        self.client.force_authenticate(user=self.student)
        enrollment_url = reverse('enrollment-list')
        self.client.post(enrollment_url, {'course_id': self.course1.id})
        
        # 查詢課程
        url = reverse('course-list')
        response = self.client.get(url)
        data = response.json()
        
        course_data = next(c for c in data['results'] if c['id'] == self.course1.id)
        self.assertEqual(course_data['enrolled_count'], 1)
        self.assertEqual(course_data['remaining_slots'], 49)


class EnrollmentAPITestCase(TestCase):
    """測試選課相關 API"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        
        # 建立測試使用者
        self.student1 = User.objects.create_user(
            username='student001',
            password='password123',
            name='測試學生1',
            role='student'
        )
        self.student2 = User.objects.create_user(
            username='student002',
            password='password123',
            name='測試學生2',
            role='student'
        )
        
        # 建立測試課程
        self.course1 = Course.objects.create(
            name='資料結構',
            course_code='CS101',
            type='必修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        self.course2 = Course.objects.create(
            name='演算法',
            course_code='CS102',
            type='必修',
            capacity=1,  # 設定小容量測試額滿
            credit=3,
            semester='113上'
        )
        
        # 建立衝突的課程時間
        # course1: 週一 09:00-12:00
        CourseTimeSlot.objects.create(
            course=self.course1,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(12, 0),
            location='資訊館101'
        )
        # course2: 週一 10:00-13:00 (與course1衝突)
        CourseTimeSlot.objects.create(
            course=self.course2,
            day_of_week=1,
            start_time=time(10, 0),
            end_time=time(13, 0),
            location='資訊館201'
        )
    
    def test_enrollment_requires_auth(self):
        """測試選課需要登入"""
        url = reverse('enrollment-list')
        
        # 未登入查詢課表
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        # 未登入選課 - POST 請求可能因為 CSRF 返回 403
        response = self.client.post(url, {'course_id': self.course1.id})
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_list_my_enrollments(self):
        """測試查詢已選課程"""
        # 先選一門課
        Enrollment.objects.create(user=self.student1, course=self.course1)
        
        # 登入
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['course']['name'], '資料結構')
    
    def test_enroll_course_success(self):
        """測試成功選課"""
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        response = self.client.post(
            url,
            {'course_id': self.course1.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['user'], self.student1.id)
        self.assertEqual(data['course']['id'], self.course1.id)
        self.assertEqual(data['course']['enrolled_count'], 1)
        
        # 確認資料庫
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.student1,
                course=self.course1
            ).exists()
        )
    
    def test_enroll_course_missing_course_id(self):
        """測試選課時未提供 course_id"""
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course_id', response.json()['detail'])
    
    def test_enroll_course_not_found(self):
        """測試選不存在的課程"""
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        response = self.client.post(url, {'course_id': 9999})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('找不到課程', response.json()['detail'])
    
    def test_enroll_course_duplicate(self):
        """測試重複選課"""
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        
        # 第一次選課
        response = self.client.post(url, {'course_id': self.course1.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 第二次選課
        response = self.client.post(url, {'course_id': self.course1.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('已選過此課程', response.json()['detail'])
    
    def test_enroll_course_capacity_full(self):
        """測試選額滿的課程"""
        # 先讓 student2 選滿課程2
        Enrollment.objects.create(user=self.student2, course=self.course2)
        
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        response = self.client.post(url, {'course_id': self.course2.id})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('課程人數已滿', response.json()['detail'])
    
    def test_enroll_course_time_conflict(self):
        """測試時間衝突"""
        # 先選 course1
        Enrollment.objects.create(user=self.student1, course=self.course1)
        
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-list')
        # course2 與 course1 時間衝突（都在週一上午）
        response = self.client.post(url, {'course_id': self.course2.id})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('時間衝突', response.json()['detail'])
    
    def test_withdraw_course_success(self):
        """測試成功退選"""
        # 建立第三門課程（無時間衝突）
        course3 = Course.objects.create(
            name='機器學習',
            course_code='CS301',
            type='選修',
            capacity=40,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=course3,
            day_of_week=5,  # 週五
            start_time=time(14, 0),
            end_time=time(17, 0),
            location='理學院A101'
        )
        
        # 先選三門課（確保退選後還有至少2門）
        enrollment1 = Enrollment.objects.create(user=self.student1, course=self.course1)
        enrollment2 = Enrollment.objects.create(user=self.student1, course=self.course2)
        enrollment3 = Enrollment.objects.create(user=self.student1, course=course3)
        
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-detail', kwargs={'pk': enrollment3.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 確認已刪除
        self.assertFalse(
            Enrollment.objects.filter(id=enrollment3.id).exists()
        )
    
    def test_withdraw_course_not_found(self):
        """測試退選不存在的紀錄"""
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-detail', kwargs={'pk': 9999})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('找不到選課記錄', response.json()['detail'])
    
    def test_withdraw_course_wrong_user(self):
        """測試退選他人的課程"""
        # student2 的選課
        enrollment = Enrollment.objects.create(user=self.student2, course=self.course1)
        
        # student1 嘗試退選
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-detail', kwargs={'pk': enrollment.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('找不到選課記錄', response.json()['detail'])
    
    def test_withdraw_course_min_limit(self):
        """測試退選低於最低門數"""
        # 建立第三門課程（無時間衝突）
        course3 = Course.objects.create(
            name='資料庫系統',
            course_code='CS303',
            type='選修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=course3,
            day_of_week=5,  # 週五
            start_time=time(14, 0),
            end_time=time(17, 0),
            location='資訊館301'
        )
        
        # 只選兩門課（course1和course3，避開衝突的course2）
        enrollment1 = Enrollment.objects.create(user=self.student1, course=self.course1)
        enrollment3 = Enrollment.objects.create(user=self.student1, course=course3)
        
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-detail', kwargs={'pk': enrollment3.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(f'至少需選擇 {MIN_COURSE_LIMIT} 門課程', response.json()['detail'])
    
    def test_my_courses_endpoint(self):
        """測試 my-courses 端點"""
        # 建立第三門課程（無時間衝突）
        course3 = Course.objects.create(
            name='資料庫系統',
            course_code='CS303',
            type='選修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=course3,
            day_of_week=5,  # 週五
            start_time=time(14, 0),
            end_time=time(17, 0),
            location='資訊館301'
        )
        
        # 選課（course1和course3，避開時間衝突的course2）
        Enrollment.objects.create(user=self.student1, course=self.course1)
        Enrollment.objects.create(user=self.student1, course=course3)
        
        self.client.force_authenticate(user=self.student1)
        
        url = reverse('enrollment-my-courses')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data), 2)
        course_names = [c['name'] for c in data]
        self.assertIn('資料結構', course_names)
        self.assertIn('資料庫系統', course_names)
    
    def test_unsupported_methods(self):
        """測試不支援的 HTTP 方法"""
        enrollment = Enrollment.objects.create(user=self.student1, course=self.course1)
        self.client.force_authenticate(user=self.student1)
        
        # 不支援 GET 單一紀錄
        url = reverse('enrollment-detail', kwargs={'pk': enrollment.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # 不支援 PUT
        response = self.client.put(url, {'course_id': self.course2.id})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # 不支援 PATCH
        response = self.client.patch(url, {'course_id': self.course2.id})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)