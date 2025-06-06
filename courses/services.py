from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Course, Enrollment, CourseTimeSlot

MAX_COURSE_LIMIT = 8
MIN_COURSE_LIMIT = 2

def check_time_conflict(user, course):
    ### 使用 prefetch_related 優化查詢，取得使用者已選課程的所有時段
    enrolled_courses = Course.objects.filter(enrollments__user=user).prefetch_related('timeslots')
    
    ### 取得新課程的所有時段
    new_course_slots = course.timeslots.all() # 直接使用傳入的 course 物件

    for new_slot in new_course_slots:  # 新課程的每個時段
        for enrolled_course in enrolled_courses:  # 已選的每個課程
            for enrolled_slot in enrolled_course.timeslots.all():  # 已選課程的每個時段
                if (new_slot.day_of_week == enrolled_slot.day_of_week and  # 同一天
                    new_slot.start_time < enrolled_slot.end_time and       # 新課程開始 < 舊課程結束
                    new_slot.end_time > enrolled_slot.start_time):         # 新課程結束 > 舊課程開始
                    return True ### 有時間衝突

    
    return False ### 無時間衝突


def enroll_course(user, course_id):
    """
    定義選課服務函式。
    處理選課邏輯，包括檢查課程存在、是否已選過、課程人數上限等。
    """
    # 1. 確認課程存在，並預載時段資料
    try:
        course = Course.objects.prefetch_related('timeslots').get(pk=course_id)
    except Course.DoesNotExist:
        raise ValidationError("找不到課程。")
    
    # 2. 檢查是否已選過這門課
    if Enrollment.objects.filter(user=user, course=course).exists():
        raise ValidationError("您已選過此課程。")
    
    # 3. 檢查課程人數上限 - 使用 model 的 property
    if course.enrollment_count >= course.capacity:
        raise ValidationError("課程人數已滿，無剩餘名額。")
    
    # 4. 檢查時間衝突
    if check_time_conflict(user, course):
        raise ValidationError("選課失敗：時間衝突。")
    
    # 5. 檢查選課門數限制
    current_count = Enrollment.objects.filter(user=user).count()
    if current_count >= MAX_COURSE_LIMIT:
        raise ValidationError(f"已達選課門數上限 ({MAX_COURSE_LIMIT}門) ，無法再選。")
    
    # 6. 交易處理：新增 Enrollment
    with transaction.atomic():
        enrollment = Enrollment.objects.create(user=user, course=course)
        return enrollment
    
def withdraw_course(user, enrollment_id):
    """
    定義退選服務函式。
    處理退選邏輯，包括檢查選課記錄存在、權限驗證、最低選課門數限制等。
    """
    # 添加調試信息
    print(f"Debug - withdraw_course called with user: {user.id}, enrollment_id: {enrollment_id}, type: {type(enrollment_id)}")
    
    # 確保 enrollment_id 是整數
    try:
        enrollment_id = int(enrollment_id)
    except (ValueError, TypeError):
        print(f"Debug - Invalid enrollment_id: {enrollment_id}")
        raise ValidationError("無效的選課記錄ID。")
    
    # 查看該用戶的所有選課記錄
    user_enrollments = Enrollment.objects.filter(user=user)
    print(f"Debug - User {user.id} has enrollments: {list(user_enrollments.values_list('id', flat=True))}")
    
    # 1. 確認選課紀錄存在且屬於該使用者
    try:
        enrollment = Enrollment.objects.select_related('course').get(
            pk=enrollment_id, 
            user=user
        )
        print(f"Debug - Found enrollment: {enrollment.id} for course: {enrollment.course.name}")
    except Enrollment.DoesNotExist:
        print(f"Debug - Enrollment {enrollment_id} not found for user {user.id}")
        # 檢查該 enrollment_id 是否存在但屬於其他用戶
        try:
            other_enrollment = Enrollment.objects.get(pk=enrollment_id)
            print(f"Debug - Enrollment {enrollment_id} exists but belongs to user {other_enrollment.user.id}")
        except Enrollment.DoesNotExist:
            print(f"Debug - Enrollment {enrollment_id} does not exist at all")
        raise ValidationError("找不到選課記錄或您無權限退選此課程。")
    
    # 2. 檢查退選後不得低於2門課程
    current_count = Enrollment.objects.filter(user=user).count()
    print(f"Debug - Current enrollment count: {current_count}")
    if current_count <= MIN_COURSE_LIMIT:
        raise ValidationError(f"退選失敗：至少需選擇 {MIN_COURSE_LIMIT} 門課程。")
    
    with transaction.atomic():
        course_name = enrollment.course.name  # 保存課程名稱用於返回
        enrollment.delete()
        print(f"Debug - Successfully deleted enrollment for course: {course_name}")

        # 可以返回成功訊息或相關資訊
        return {
            'message': f'成功退選課程：{course_name}',
            'course_name': course_name,
            'remaining_enrollments': current_count - 1
        }