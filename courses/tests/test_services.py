from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import time

from courses.models import Course, Enrollment, CourseTimeSlot
from courses.services import (
    enroll_course, 
    withdraw_course, 
    check_time_conflict,
    MAX_COURSE_LIMIT,
    MIN_COURSE_LIMIT
)

User = get_user_model()


class EnrollmentServiceTestCase(TestCase):
    """測試選課相關的業務邏輯"""
    
    def setUp(self):
        """設置測試環境"""
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
            capacity=2,  # 設定小容量方便測試
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
            name='機器學習',
            course_code='CS301',
            type='選修',
            capacity=40,
            credit=3,
            semester='113上'
        )
        
        # 建立課程時間
        # 課程1: 週一、週三 09:00-12:00
        CourseTimeSlot.objects.create(
            course=self.course1,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(12, 0),
            location='資訊館101'
        )
        CourseTimeSlot.objects.create(
            course=self.course1,
            day_of_week=3,
            start_time=time(9, 0),
            end_time=time(12, 0),
            location='資訊館101'
        )
        
        # 課程2: 週二、週四 14:00-17:00
        CourseTimeSlot.objects.create(
            course=self.course2,
            day_of_week=2,
            start_time=time(14, 0),
            end_time=time(17, 0),
            location='資訊館201'
        )
        CourseTimeSlot.objects.create(
            course=self.course2,
            day_of_week=4,
            start_time=time(14, 0),
            end_time=time(17, 0),
            location='資訊館201'
        )
        
        # 課程3: 週五 10:00-13:00 (避免與其他課程衝突)
        CourseTimeSlot.objects.create(
            course=self.course3,
            day_of_week=5,
            start_time=time(10, 0),
            end_time=time(13, 0),
            location='理學院A205'
        )
    
    def test_enroll_course_success(self):
        """測試成功選課"""
        enrollment = enroll_course(self.student1, self.course1.id)
        
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.user, self.student1)
        self.assertEqual(enrollment.course, self.course1)
        
        # 確認資料庫中有該紀錄
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.student1,
                course=self.course1
            ).exists()
        )
    
    def test_enroll_course_not_found(self):
        """測試選課時課程不存在"""
        with self.assertRaises(ValidationError) as cm:
            enroll_course(self.student1, 9999)  # 不存在的課程ID
        
        self.assertIn('找不到課程', str(cm.exception))
    
    def test_enroll_course_already_enrolled(self):
        """測試重複選課"""
        # 先選一次
        enroll_course(self.student1, self.course1.id)
        
        # 再選一次應該失敗
        with self.assertRaises(ValidationError) as cm:
            enroll_course(self.student1, self.course1.id)
        
        self.assertIn('已選過此課程', str(cm.exception))
    
    def test_enroll_course_capacity_full(self):
        """測試課程額滿"""
        # 先讓其他學生選滿課程 (capacity=2)
        enroll_course(self.student1, self.course1.id)
        enroll_course(self.student2, self.course1.id)
        
        # 第三個學生應該無法選課
        student3 = User.objects.create_user(
            username='student003',
            password='password123',
            name='測試學生3',
            role='student'
        )
        
        with self.assertRaises(ValidationError) as cm:
            enroll_course(student3, self.course1.id)
        
        self.assertIn('課程人數已滿', str(cm.exception))
    
    def test_enroll_course_time_conflict(self):
        """測試時間衝突"""
        # 先選課程1
        enroll_course(self.student1, self.course1.id)
        
        # 建立一個與課程1時間衝突的新課程
        conflict_course = Course.objects.create(
            name='衝突課程',
            course_code='CONFLICT01',
            type='選修',
            capacity=30,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=conflict_course,
            day_of_week=1,  # 週一，與course1相同
            start_time=time(10, 0),  # 在course1的時間內
            end_time=time(11, 0),
            location='其他教室'
        )
        
        # 選衝突課程應該失敗
        with self.assertRaises(ValidationError) as cm:
            enroll_course(self.student1, conflict_course.id)
        
        self.assertIn('時間衝突', str(cm.exception))
    
    def test_enroll_course_max_limit(self):
        """測試選課門數上限"""
        # 先選前3門已存在的課程
        courses_to_enroll = [self.course1, self.course2, self.course3]
        for course in courses_to_enroll:
            enroll_course(self.student1, course.id)
        
        # 建立更多課程以達到上限 (從第4門開始)
        # 已使用時間：
        # - 週一 09:00-12:00 (course1)
        # - 週二 14:00-17:00 (course2)
        # - 週三 09:00-12:00 (course1)
        # - 週四 14:00-17:00 (course2)
        # - 週五 10:00-13:00 (course3)
        
        for i in range(4, MAX_COURSE_LIMIT + 2):
            course = Course.objects.create(
                name=f'測試課程{i}',
                course_code=f'TEST{i:03d}',
                type='選修',
                capacity=50,
                credit=3,
                semester='113上'
            )
            
            # 使用完全不同的時段
            if i == 4:
                # 週一下午
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=1,
                    start_time=time(14, 0),
                    end_time=time(16, 0),
                    location=f'教室{i}'
                )
            elif i == 5:
                # 週二早上
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=2,
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    location=f'教室{i}'
                )
            elif i == 6:
                # 週三下午
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=3,
                    start_time=time(14, 0),
                    end_time=time(16, 0),
                    location=f'教室{i}'
                )
            elif i == 7:
                # 週四早上
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=4,
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    location=f'教室{i}'
                )
            elif i == 8:
                # 週五早上（在course3之前）
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=5,
                    start_time=time(8, 0),
                    end_time=time(9, 30),
                    location=f'教室{i}'
                )
            else:
                # 週五下午或週六
                CourseTimeSlot.objects.create(
                    course=course,
                    day_of_week=5 if i == 9 else 6,
                    start_time=time(14, 0) if i == 9 else time(9, 0),
                    end_time=time(16, 0) if i == 9 else time(11, 0),
                    location=f'教室{i}'
                )
            
            if Enrollment.objects.filter(user=self.student1).count() < MAX_COURSE_LIMIT:
                enroll_course(self.student1, course.id)
        
        # 確認已達上限
        self.assertEqual(
            Enrollment.objects.filter(user=self.student1).count(),
            MAX_COURSE_LIMIT
        )
        
        # 再選應該失敗
        last_course = Course.objects.create(
            name='超過上限的課程',
            course_code='OVER_LIMIT',
            type='選修',
            capacity=50,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=last_course,
            day_of_week=6,
            start_time=time(14, 0),
            end_time=time(16, 0),
            location='教室X'
        )
        
        with self.assertRaises(ValidationError) as cm:
            enroll_course(self.student1, last_course.id)
        
        self.assertIn('已達選課門數上限', str(cm.exception))
    
    def test_check_time_conflict_no_conflict(self):
        """測試時間衝突檢查 - 無衝突"""
        # 選課程1
        enroll_course(self.student1, self.course1.id)
        
        # 檢查課程2（不同時間）
        has_conflict = check_time_conflict(self.student1, self.course2)
        self.assertFalse(has_conflict)
    
    def test_check_time_conflict_with_conflict(self):
        """測試時間衝突檢查 - 有衝突"""
        # 選課程1
        enroll_course(self.student1, self.course1.id)
        
        # 建立一個與課程1時間衝突的新課程
        conflict_course = Course.objects.create(
            name='衝突課程',
            course_code='CONFLICT01',
            type='選修',
            capacity=30,
            credit=3,
            semester='113上'
        )
        CourseTimeSlot.objects.create(
            course=conflict_course,
            day_of_week=1,  # 週一，與course1相同
            start_time=time(10, 0),  # 在course1的時間內
            end_time=time(11, 0),
            location='其他教室'
        )
        
        # 檢查衝突課程（週一時間重疊）
        has_conflict = check_time_conflict(self.student1, conflict_course)
        self.assertTrue(has_conflict)
    
    def test_withdraw_course_success(self):
        """測試成功退選"""
        # 先選三門課（確保退選後還有至少2門）
        enroll_course(self.student1, self.course1.id)
        enroll_course(self.student1, self.course2.id)
        enrollment3 = enroll_course(self.student1, self.course3.id)
        
        # 確認目前有3門課
        self.assertEqual(
            Enrollment.objects.filter(user=self.student1).count(),
            3
        )
        
        # 退選第三門
        result = withdraw_course(self.student1, enrollment3.id)
        
        self.assertIn('成功退選', result['message'])
        self.assertEqual(result['course_name'], self.course3.name)
        self.assertEqual(result['remaining_enrollments'], 2)
        
        # 確認資料庫中已刪除
        self.assertFalse(
            Enrollment.objects.filter(
                user=self.student1,
                course=self.course3
            ).exists()
        )
        
        # 確認剩餘2門課
        self.assertEqual(
            Enrollment.objects.filter(user=self.student1).count(),
            2
        )
    
    def test_withdraw_course_not_found(self):
        """測試退選時紀錄不存在"""
        with self.assertRaises(ValidationError) as cm:
            withdraw_course(self.student1, 9999)
        
        self.assertIn('找不到選課記錄', str(cm.exception))
    
    def test_withdraw_course_wrong_user(self):
        """測試退選他人的課程"""
        # student1 選課
        enrollment = enroll_course(self.student1, self.course1.id)
        
        # student2 嘗試退選
        with self.assertRaises(ValidationError) as cm:
            withdraw_course(self.student2, enrollment.id)
        
        self.assertIn('找不到選課記錄', str(cm.exception))
    
    def test_withdraw_course_min_limit(self):
        """測試退選後低於最低門數限制"""
        # 只選兩門課（最低限制）
        enroll_course(self.student1, self.course1.id)
        enrollment2 = enroll_course(self.student1, self.course2.id)
        
        # 嘗試退選應該失敗
        with self.assertRaises(ValidationError) as cm:
            withdraw_course(self.student1, enrollment2.id)
        
        self.assertIn(f'至少需選擇 {MIN_COURSE_LIMIT} 門課程', str(cm.exception))
    
    def test_transaction_atomicity(self):
        """測試交易的原子性"""
        # 建立一個會在中途失敗的情況
        # 使用 mock 或其他方式模擬失敗
        
        initial_count = Enrollment.objects.count()
        
        try:
            with transaction.atomic():
                enroll_course(self.student1, self.course1.id)
                # 強制引發錯誤
                raise Exception("模擬錯誤")
        except Exception:
            pass
        
        # 確認沒有新增任何紀錄
        self.assertEqual(Enrollment.objects.count(), initial_count)
    
    def test_concurrent_enrollment(self):
        """測試並發選課情況"""
        # 這個測試比較複雜，可能需要使用 threading 或其他方式
        # 簡化版本：確保選課數不會超過容量
        
        # 設定容量為1
        self.course1.capacity = 1
        self.course1.save()
        
        # 第一個學生選課成功
        enroll_course(self.student1, self.course1.id)
        
        # 第二個學生應該失敗
        with self.assertRaises(ValidationError) as cm:
            enroll_course(self.student2, self.course1.id)
        
        self.assertIn('課程人數已滿', str(cm.exception))