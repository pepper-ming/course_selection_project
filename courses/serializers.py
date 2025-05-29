from rest_framework import serializers
from .models import Course, Enrollment, CourseTimeSlot
from accounts.models import User

### 因為 timeslots 會被 CourseSerializer 用到，所以要先寫
class CourseTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseTimeSlot
        fields = ['day_of_week', 'start_time', 'end_time', 'location']

### enrolled_count 和 remaining_slots 不是 DB 欄位，要自訂 Serializer Method Field
### type 欄位要記得Enum檢查在Model層處理，Serializer可驗證但主要邏輯應該在Model或Service
class CourseSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.SerializerMethodField()
    remaining_slots = serializers.SerializerMethodField()

    ### source='coursetimeslot_set' 指定ForeignKey反查
    timeslots = CourseTimeSlotSerializer(many=True, source='timeslots')

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'course_code', 'type', 'capacity', 'credit','semester',
            'description', 'enrolled_count', 'remaining_slots', 'timeslots'
        ]
    
    ### 因為 model 裡面已經有寫 property，直接用就好，不用再查詢

    def get_enrolled_count(self, obj):
        return obj.enrollment_count
    
    def get_remaining_slots(self, obj):
        return obj.remaining_capacity

class EnrollmentSerializer(serializers.ModelSerializer):
    """
    API需求:
        id, user, course (用 CourseSerializer 包 nested)
        選課時僅需 course_id (POST)，但查詢/回應要有詳細課程資料
    """
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True
    )
    user = serializers.PrimaryKeyRelatedField(read_only=True) # 或用 UserSerializer

    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course', 'course_id']
    
    """
    讀取時回傳課程詳細資訊(course=CourseSerializer)

    新增時只需傳 course_id(寫入用、API規格一致)

    user欄位 read_only 從 request.user 取得
    """