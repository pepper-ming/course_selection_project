from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class LoginSerializer(serializers.Serializer):
    """登入序列化器"""
    username = serializers.CharField(
        required=True,
        help_text="使用者帳號 (學號或 Email)"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="使用者密碼"
    )

    def validate(self, attrs):
        """驗證使用者帳號和密碼"""
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                raise serializers.ValidationError('無效的帳號或密碼。')
            
            if not user.is_active:
                raise serializers.ValidationError('此帳號已被停用。')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('必須提供帳號和密碼。')
        
class UserSerializer(serializers.ModelSerializer):
    """使用者資料序列化器"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'email',
            'role', 'role_display', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']