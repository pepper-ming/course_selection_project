from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
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
        
        return queryset.prefetch_related('timeslots').order_by('id')
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'search', 
                openapi.IN_QUERY, 
                description="課程名稱關鍵字搜尋", 
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'type', 
                openapi.IN_QUERY, 
                description="課程類型篩選 (必修/選修)", 
                type=openapi.TYPE_STRING,
                enum=['必修', '選修']
            ),
            openapi.Parameter(
                'semester', 
                openapi.IN_QUERY, 
                description="開課學期篩選", 
                type=openapi.TYPE_STRING
            ),
        ]
    )
    
    def list(self, request, *args, **kwargs):
        """
        覆寫 list 方法以符合 API 規格的回應格式
        回傳 {"count": <課程數量>, "results": <課程列表>}
        """
        queryset = self.filter_queryset(self.get_queryset())

        # 分頁處理
        page = self.paginate_queryset(queryset) # settings.py 設定每頁 20 筆
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # 無分頁時的回應格式
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

# 為整個 ViewSet 添加 CSRF exemption
@method_decorator(csrf_exempt, name='dispatch')
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
        # 為 Swagger 文件生成添加檢查
        if getattr(self, 'swagger_fake_view', False):
            # 在 Swagger 文件生成時返回空的 QuerySet
            return Enrollment.objects.none()
        
        return Enrollment.objects.filter(
            user=self.request.user
        ).select_related('course').prefetch_related('course__timeslots')

    @swagger_auto_schema(
            operation_description="查詢學生已選的課程列表",
            responses={
                200: openapi.Response(
                    description="成功取得列表",
                    schema=openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'course_code': openapi.Schema(type=openapi.TYPE_STRING),
                                'type': openapi.Schema(type=openapi.TYPE_STRING),
                                'timeslots': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'day_of_week': openapi.Schema(type=openapi.TYPE_STRING),
                                            'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='openapi.FORMAT_TIME'),
                                            'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='openapi.FORMAT_TIME'),
                                            'location': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                )
                            }
                        )
                    )
                ),
                401: "未授權，請先登入"
            }
    )
    
    def list(self, request, *args, **kwargs):
        """
        查詢課表 - GET /api/enrollments/
        回傳學生已選的課程列表(只回傳課程資料,不含選課紀錄ID)
        """
        enrollments = self.get_queryset()
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="學生選課",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['course_id'],
            properties={
                'course_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='欲選課程的ID',
                    example=1
                )
            }
        ),
        responses={
            201: openapi.Response(
                description="選課成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'course': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'course_code': openapi.Schema(type=openapi.TYPE_STRING),
                                'type': openapi.Schema(type=openapi.TYPE_STRING),
                                'capacity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'enrolled_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'remaining_slots': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'timeslots': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'day_of_week': openapi.Schema(type=openapi.TYPE_STRING),
                                            'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='openapi.FORMAT_TIME'),
                                            'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='openapi.FORMAT_TIME'),
                                            'location': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                )
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="選課失敗",
                examples={
                    "application/json": {
                        "detail": "選課失敗：課程人數已滿，無剩餘名額。"
                    }
                }
            ),
            401: "未授權，請先登入",
            404: "課程不存在"
        }
    )
    
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
            # 直接實例化 serializer 而不是使用 get_serializer，因為這裡需要的是新建的選課紀錄
            serializer = EnrollmentSerializer(enrollment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            import traceback
            print(f"選課錯誤: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'detail': f'選課失敗：{str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @swagger_auto_schema(
        operation_description="退選課程",
        manual_parameters=[
            openapi.Parameter(
                'id', 
                openapi.IN_PATH, 
                description="選課紀錄 ID", 
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            204: "退選成功",
            400: openapi.Response(
                description="退選失敗",
                examples={
                    "application/json": {
                        "detail": "退選失敗:學生至少需保留2門課程。"
                    }
                }
            ),
            401: "未授權，請先登入",
            404: "選課紀錄不存在"
        }
    )
    
    def destroy(self, request, *args, **kwargs):
        """
        退選 - DELETE /api/enrollments/<id>/
        """
        try:
            enrollment_id = kwargs.get('pk')
            print(f"嘗試退選 enrollment_id: {enrollment_id}, user: {request.user.id}")
            result = withdraw_course(request.user, enrollment_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            print(f"退選驗證錯誤: {str(e)}")
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            print(f"退選系統錯誤: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
        enrollments = self.get_queryset()
        courses = [enrollment.course for enrollment in enrollments]
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)