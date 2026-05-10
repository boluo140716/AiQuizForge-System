from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotebookViewSet, NoteViewSet,QuizViewSet,WrongQuestionViewSet

router = DefaultRouter()
router.register(r'notebooks', NotebookViewSet, basename='notebook')  # 注册笔记本视图集
router.register(r'notes', NoteViewSet, basename='note')  # 注册笔记视图集 
router.register(r'quizzes', QuizViewSet, basename='quiz')  # 注册测验视图集
router.register(r'wrong-questions', WrongQuestionViewSet, basename='wrong-question')  # 注册错题视图集

urlpatterns = [
    path('', include(router.urls)),  
]