from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='邮箱')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    display_name = models.CharField(max_length=50, blank=True, verbose_name='显示名称')

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username