from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import LoginSerializer, UserSerializer, RegisterSerializer
from .models import User

try:
    from rest_framework_simplejwt.tokens import RefreshToken
    JWT_ENABLED = True
except ImportError:
    JWT_ENABLED = False

class LoginView(APIView):
    """
    使用者登入端點
    支援 Session 和 JWT Token 兩種認證方式
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="登入成功",
                examples={
                    "application/json": {
                        "user": {
                            "id": 1,
                            "username": "student001",
                            "name": "王小明",
                            "role": "student"
                        },
                        "token": {
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
                        },
                        "message": "登入成功"
                    }
                }
            ),
            400: "登入失敗"
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Session 認證
            login(request, user)

            response_data = {
                'user': UserSerializer(user).data,
                'message': '登入成功'
            }

            # 如果啟用 JWT，額外回傳 tokens
            if JWT_ENABLED and request.data.get('use_jwt', False):
                refresh = RefreshToken.for_user(user)
                response_data['token'] = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(
            {'detail': '登入失敗', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class LogoutView(APIView):
    """
    使用者登出端點
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="登出成功",
                examples={
                    "application/json": {
                        "message": "登出成功"
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        # Session 登出
        logout(request)

        # 如果使用 JWT，可以在前端刪除 token
        # 或實作 token 黑名單功能

        return Response(
            {'message': '登出成功'},
            status=status.HTTP_200_OK
        )

class CurrentUserView(APIView):
    """
    取得當前登入使用者資訊
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: UserSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    """
    使用者註冊端點（選用）
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={
            201: openapi.Response(
                description="註冊成功",
                examples={
                    "application/json": {
                        "user": {
                            "id": 1,
                            "username": "student001",
                            "name": "王小明",
                            "role": "student"
                        },
                        "message": "註冊成功"
                    }
                }
            )
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'user': UserSerializer(user).data,
                'message': '註冊成功'
            },
            status=status.HTTP_201_CREATED
        )

# JWT Token 相關視圖（如果使用 JWT）
if JWT_ENABLED:
    from rest_framework_simplejwt.views import (
        TokenObtainPairView,
        TokenRefreshView,
    )
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
    
    class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
        """自訂 JWT Token 序列化器，加入使用者資訊"""
        def validate(self, attrs):
            data = super().validate(attrs)
            
            # 加入使用者資訊
            data['user'] = UserSerializer(self.user).data
            
            return data
    
    class CustomTokenObtainPairView(TokenObtainPairView):
        """自訂 JWT 登入視圖"""
        serializer_class = CustomTokenObtainPairSerializer