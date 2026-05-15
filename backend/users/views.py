from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User
from .serializers import RegisterSerializer, UserSerializer, UserProfileSerializer, ProfileUpdateSerializer
from django.db.models import Avg
from notes.models import Note, QuizAttempt, WrongQuestion

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()  # 注册视图，允许匿名用户访问
    permission_classes = (permissions.AllowAny,)  # 允许匿名用户访问
    serializer_class = RegisterSerializer  # 使用自定义的注册序列化器

class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'avatar' in data:
            request.user.avatar = data['avatar']
        if 'display_name' in data:
            request.user.display_name = data['display_name']

        request.user.save()

        user_serializer = UserSerializer(request.user, context={'request': request})
        return Response(user_serializer.data)

class ProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request):
        user=request.user
        #统计用户笔记数量
        total_notes = Note.objects.filter(user=user).count()
        #统计测验数
        from notes.models import  Quiz
        total_quizzes = Quiz.objects.filter(user=user,status='completed').count()
        #平均正确率
        avg_rate = QuizAttempt.objects.filter(user=user).aggregate(
            avg=Avg('correct_rate')
        )['avg'] or 0.0
        #统计错题数
        total_wrong = WrongQuestion.objects.filter(user=user).values('question').distinct().count()
        #创建序列化器
        serializer = UserProfileSerializer({
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'email': user.email,
            'avatar': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            'date_joined': user.date_joined,
            'total_notes': total_notes,
            'total_quizzes': total_quizzes,
            'avg_correct_rate': round(avg_rate, 2),
            'total_wrong_questions': total_wrong,
        })

        return Response(serializer.data)