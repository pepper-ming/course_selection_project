from django.db import models
from accounts.models import User

class Course(models.Model):
    COURSE_TYPE_CHOICES = (
        ('必修', '必修'),
        ('選修', '選修'),
    )
    
    name = models.CharField('課程名稱', max_length=100)
    course_code = models.CharField('課程代碼', max_length=20, unique=True)
    type = models.CharField('課程類型', max_length=10, choices=COURSE_TYPE_CHOICES)
    capacity = models.PositiveIntegerField('人數上限')
    credit = models.PositiveIntegerField('學分數')
    description = models.TextField('課程簡介', blank=True)
    semester = models.CharField('開課學期', max_length=10, blank=True, null=True)
    teacher = models.ForeignKey(
        User, related_name = 'courses_taught', null=True, blank=True, on_delete=models.SET_NULL,
        limit_choices_to={'role': 'teacher'}
    )

    def __str__(self):
        return f"{self.name}({self.course_code})"
    
    @property
    def enrollment_count(self):
        return self.enrollments.count()
    
    @property
    def remaining_capacity(self):
        return self.capacity - self.enrollment_count


class CourseTimeSlot(models.Model):
    DAYS_OF_WEEK = (
        (1, '星期一'),
        (2, '星期二'),
        (3, '星期三'),
        (4, '星期四'),
        (5, '星期五'),
        (6, '星期六'),
        (7, '星期日'),
    )

    course = models.ForeignKey(Course, related_name='timeslots', on_delete=models.CASCADE)
    day_of_week = models.PositiveSmallIntegerField('星期', choices=DAYS_OF_WEEK)
    start_time = models.TimeField('開始時間')
    end_time = models.TimeField('結束時間')
    location = models.CharField('上課地點', max_length=100, blank=True)

    class Meta:
        unique_together = ('course', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time} - {self.end_time} ({self.course.name})"

class Enrollment(models.Model):
    user = models.ForeignKey(User, related_name='enrollments', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='enrollments', on_delete=models.CASCADE)
    enroll_time = models.DateTimeField('選課時間', auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
    
    def __str__(self):
        return f"{self.user.username} -> {self.course.name}"