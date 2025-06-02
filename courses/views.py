from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Course, Enrollment
from .serializers import CourseSerializer, EnrollmentSerializer
from .services import enroll_course, withdraw_course
from django.core.exceptions import ValidationError

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    課程查詢 ViewSet
    提供課程列表查詢功能，支援搜尋、類型篩選、學期篩選
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        # 搜尋功能
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # 類型篩選
        course_type = self.request.query_params.get('type', None)
        if course_type in ['必修', '選修']:
            queryset = queryset.filter(type=course_type)

        # 開課學期篩選
        semester = self.request.query_params.get('semester', None)
        if semester:
            queryset = queryset.filter(semester=semester)
        
        return queryset.prefetch_related('timeslots')
    
    def list(self, request, *args, **kwargs):
        """
        覆寫 list 方法以符合 API 規格的回應格式
        回傳 {"count": <課程數量>, "results": <課程列表>}
        """
        queryset = self.filter_queryset(self.get_queryset())

        # 分頁處理
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # 無分頁時的回應格式
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

class EnrollmentViewSet(viewsets.ViewSet):
    """
    選課管理 ViewSet
    處理選課、退選、查詢課表等功能
    """
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    # 設定 lookup_field 為預設的 'pk'
    lookup_field = 'pk'

    def get_queryset(self):
        """只顯示當前使用者的選課紀錄"""
        return Enrollment.objects.filter(
            user=self.request.user
        ).select_related('course').prefetch_related('course__timeslots')
    
    def list(self, request, *args, **kwargs):
        """
        查詢課表 - GET /api/enrollments/
        回傳學生已選的課程列表(只回傳課程資料,不含選課紀錄ID)
        """
        enrollments = self.get_queryset()
        courses = [enrollment.course for enrollment in enrollments]
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        選課 - POST /api/enrollments/
        Request body: {"course_id": 1}
        """
        try:
            course_id = request.data.get('course_id')
            if not course_id:
                return Response(
                    {'detail': '請提供 course_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            enrollment = enroll_course(request.user, course_id)
            serializer = self.get_serializer(enrollment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                {'detail': '選課失敗：系統錯誤'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    
    def destroy(self, request, *args, **kwargs):
        """
        退選 - DELETE /api/enrollments/<id>/
        """
        try:
            enrollment_id = kwargs.get('pk')
            result = withdraw_course(request.user, enrollment_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                {'detail': '退選失敗：系統錯誤'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # 停用不需要的方法
    def retrieve(self, request, *args, **kwargs):
        """不提供單一選課紀錄查詢"""
        return Response(
            {'detail': '不支援此操作。'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        """不提供更新功能"""
        return Response(
            {'detail': '不支援此操作。'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """不提供部分更新功能"""
        return Response(
            {'detail': '不支援此操作。'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=False, methods=['get'], url_path='my-courses')
    def my_courses(self, request):
        """
        額外提供的端點: GET /api/enrollments/my-courses/
        另一種查詢課表的方式，回傳格式與 list 相同
        """
        return self.list(request)