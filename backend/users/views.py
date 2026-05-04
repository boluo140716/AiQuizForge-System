from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User
from .serializers import RegisterSerializer, UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()  # 注册视图，允许匿名用户访问
    permission_classes = (permissions.AllowAny,)  # 允许匿名用户访问
    serializer_class = RegisterSerializer  # 使用自定义的注册序列化器

class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)