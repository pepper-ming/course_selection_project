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

class RegisterSerializer(serializers.ModelSerializer):
    """註冊序列化器（選用）"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        help_text="密碼至少8個字元"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="確認密碼"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'password', 'password_confirm',
            'name', 'email', 'role'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'role': {'default': 'student'}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密碼與確認密碼不符")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')  # 移除確認密碼欄位（不需要儲存到資料庫）
        user = User.objects.create_user(**validated_data)
        """
        create_user() 而非 create(), create_user() 會自動將密碼進行雜湊處理(Django 標準做法)
        """
        return user