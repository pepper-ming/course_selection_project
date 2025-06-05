from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import time
import random

from courses.models import Course, CourseTimeSlot, Enrollment

User = get_user_model()


class Command(BaseCommand):
    help = '建立測試資料（使用者、課程、時間時段）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除現有資料後再建立',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('清除現有資料...')
            Enrollment.objects.all().delete()
            CourseTimeSlot.objects.all().delete()
            Course.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        with transaction.atomic():
            # 建立使用者
            self.stdout.write('建立使用者...')
            users = self.create_users()
            
            # 建立課程
            self.stdout.write('建立課程...')
            courses = self.create_courses()
            
            # 建立課程時間
            self.stdout.write('建立課程時間時段...')
            self.create_course_timeslots(courses)
            
            # 建立一些選課紀錄（示範用）
            self.stdout.write('建立選課紀錄...')
            self.create_sample_enrollments(users['students'], courses)

        self.stdout.write(self.style.SUCCESS('測試資料建立完成！'))

    def create_users(self):
        users = {
            'students': [],
            'teachers': [],
            'admin': None
        }

        # 建立管理員
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'name': '系統管理員',
                'role': 'admin',
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(f'  建立管理員: {admin.username}')
        users['admin'] = admin

        # 建立教師
        teacher_data = [
            {'username': 'teacher001', 'name': '陳教授', 'email': 'chen@example.com'},
            {'username': 'teacher002', 'name': '林副教授', 'email': 'lin@example.com'},
            {'username': 'teacher003', 'name': '王助理教授', 'email': 'wang@example.com'},
        ]
        
        for data in teacher_data:
            teacher, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'name': data['name'],
                    'role': 'teacher',
                    'email': data['email'],
                }
            )
            if created:
                teacher.set_password('password123')
                teacher.save()
                self.stdout.write(f'  建立教師: {teacher.name}')
            users['teachers'].append(teacher)

        # 建立學生
        for i in range(1, 21):  # 建立 20 個學生
            username = f'student{i:03d}'
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'name': f'學生{i}',
                    'role': 'student',
                    'email': f'{username}@example.com',
                }
            )
            if created:
                student.set_password('password123')
                student.save()
                self.stdout.write(f'  建立學生: {student.name}')
            users['students'].append(student)

        return users

    def create_courses(self):
        courses_data = [
            # 必修課程
            {
                'name': '資料結構',
                'course_code': 'CS101',
                'type': '必修',
                'capacity': 60,
                'credit': 3,
                'description': '介紹基本資料結構如陣列、鏈結串列、堆疊、佇列、樹、圖等',
                'semester': '113上',
            },
            {
                'name': '演算法',
                'course_code': 'CS102',
                'type': '必修',
                'capacity': 60,
                'credit': 3,
                'description': '介紹演算法設計與分析，包含排序、搜尋、動態規劃等',
                'semester': '113上',
            },
            {
                'name': '作業系統',
                'course_code': 'CS201',
                'type': '必修',
                'capacity': 50,
                'credit': 3,
                'description': '介紹作業系統原理，包含行程管理、記憶體管理、檔案系統等',
                'semester': '113上',
            },
            {
                'name': '線性代數',
                'course_code': 'MATH201',
                'type': '必修',
                'capacity': 80,
                'credit': 3,
                'description': '向量空間、線性轉換、矩陣運算、特徵值與特徵向量',
                'semester': '113上',
            },
            # 選修課程
            {
                'name': '機器學習導論',
                'course_code': 'CS301',
                'type': '選修',
                'capacity': 40,
                'credit': 3,
                'description': '監督式學習、非監督式學習、深度學習基礎',
                'semester': '113上',
            },
            {
                'name': '網頁程式設計',
                'course_code': 'CS302',
                'type': '選修',
                'capacity': 45,
                'credit': 3,
                'description': 'HTML、CSS、JavaScript、前端框架介紹',
                'semester': '113上',
            },
            {
                'name': '資料庫系統',
                'course_code': 'CS303',
                'type': '選修',
                'capacity': 50,
                'credit': 3,
                'description': '關聯式資料庫、SQL、正規化、交易處理',
                'semester': '113上',
            },
            {
                'name': '人工智慧',
                'course_code': 'CS304',
                'type': '選修',
                'capacity': 40,
                'credit': 3,
                'description': '搜尋演算法、知識表示、專家系統、自然語言處理',
                'semester': '113上',
            },
            {
                'name': '統計學',
                'course_code': 'STAT101',
                'type': '選修',
                'capacity': 60,
                'credit': 3,
                'description': '敘述統計、機率分配、假設檢定、迴歸分析',
                'semester': '113上',
            },
            {
                'name': '深度學習',
                'course_code': 'CS401',
                'type': '選修',
                'capacity': 35,
                'credit': 3,
                'description': '神經網路、CNN、RNN、Transformer架構',
                'semester': '113上',
            },
        ]

        courses = []
        for data in courses_data:
            course, created = Course.objects.get_or_create(
                course_code=data['course_code'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  建立課程: {course.name} ({course.course_code})')
            courses.append(course)

        return courses

    def create_course_timeslots(self, courses):
        # 定義一些常見的上課時段
        time_slots = [
            # 早上時段
            {'start': time(8, 0), 'end': time(10, 0)},
            {'start': time(10, 0), 'end': time(12, 0)},
            # 下午時段
            {'start': time(13, 0), 'end': time(15, 0)},
            {'start': time(15, 0), 'end': time(17, 0)},
            # 晚上時段
            {'start': time(18, 0), 'end': time(20, 0)},
        ]

        locations = ['資訊館101', '資訊館201', '理學院A205', '理學院B301', '綜合大樓401']

        for course in courses:
            # 每門課程隨機分配 1-2 個時段
            num_slots = random.randint(1, 2)
            used_days = []

            for _ in range(num_slots):
                # 隨機選擇星期幾（避免重複）
                available_days = [d for d in range(1, 6) if d not in used_days]  # 週一到週五
                if not available_days:
                    break
                    
                day = random.choice(available_days)
                used_days.append(day)
                
                # 隨機選擇時段和教室
                time_slot = random.choice(time_slots)
                location = random.choice(locations)

                CourseTimeSlot.objects.get_or_create(
                    course=course,
                    day_of_week=day,
                    start_time=time_slot['start'],
                    defaults={
                        'end_time': time_slot['end'],
                        'location': location,
                    }
                )
                self.stdout.write(f'    {course.name}: 星期{day} {time_slot["start"]}-{time_slot["end"]} @ {location}')

    def create_sample_enrollments(self, students, courses):
        # 為前 10 個學生建立一些選課紀錄
        for student in students[:10]:
            # 每個學生選 2-4 門課
            num_courses = random.randint(2, 4)
            selected_courses = random.sample(courses, num_courses)
            
            for course in selected_courses:
                try:
                    Enrollment.objects.create(
                        user=student,
                        course=course
                    )
                    self.stdout.write(f'  {student.name} 選修 {course.name}')
                except Exception as e:
                    # 可能因為重複選課或其他原因失敗
                    pass