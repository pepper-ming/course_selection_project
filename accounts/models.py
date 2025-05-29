from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', '學生'),
        ('teacher', '老師'),
        ('admin', '管理員'),
    )

    name = models.CharField('姓名', max_length=100)
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='student')
    email = models.EmailField('電子郵件', blank=True, null=True)

    # date_joined, username, password 都繼承自 AbstractUser
    ### 使用 AbstractUser 好處是直接整合 Django 認證系統

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"
