from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Avg, Count
from notes.models import QuizAttempt, WrongQuestion,Note

class RegisterSerializer(serializers.ModelSerializer):  # 自定义注册序列化器
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    email= serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')  

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "两次密码不一致"})  
        return attrs  

    def create(self, validated_data):  # 重写create方法，创建用户时自动设置密码
        validated_data.pop('password2')  # 移除password2字段
        user = User.objects.create_user(**validated_data)  
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class UserProfileSerializer(serializers.Serializer):
    id=serializers.IntegerField(read_only=True)
    username=serializers.CharField(read_only=True)
    email=serializers.EmailField(read_only=True)
    date_joined=serializers.DateTimeField(read_only=True)

    #学习统计
    #总笔记数
    total_notes=serializers.IntegerField(read_only=True)
    #总测验数
    total_quizzes=serializers.IntegerField(read_only=True)
    #总错题数
    total_wrong_questions=serializers.IntegerField(read_only=True)
    #平均正确率
    avg_correct_rate=serializers.FloatField(read_only=True)
