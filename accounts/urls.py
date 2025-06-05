from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    CurrentUserView,
    RegisterView,
)

urlpatterns = [
    # Session-based 認證
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/register/', RegisterView.as_view(), name='register'),
]

# 如果使用 JWT Token
try:
    from rest_framework_simplejwt.views import TokenRefreshView
    from .views import CustomTokenObtainPairView
    
    # JWT 相關端點
    jwt_urlpatterns = [
        path('auth/jwt/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('auth/jwt/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    ]
    
    urlpatterns += jwt_urlpatterns
except ImportError:
    pass