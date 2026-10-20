from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotebookViewSet, NoteViewSet, QuizViewSet, WrongQuestionViewSet,
    MasteryView, LearningCurveView, ReviewDueView, ReviewPracticeView,
    ImportNotesView, ExportQuestionsView,
)
from .sse import quiz_progress_stream

router = DefaultRouter()
router.register(r'notebooks', NotebookViewSet, basename='notebook')  # 注册笔记本视图集
router.register(r'notes', NoteViewSet, basename='note')  # 注册笔记视图集 
router.register(r'quizzes', QuizViewSet, basename='quiz')  # 注册测验视图集
router.register(r'wrong-questions', WrongQuestionViewSet, basename='wrong-question')  # 注册错题视图集

urlpatterns = [
    path('quizzes/<int:quiz_id>/stream/', quiz_progress_stream, name='quiz-progress-stream'),
    path('learning/mastery/', MasteryView.as_view(), name='mastery'),
    path('learning/curve/', LearningCurveView.as_view(), name='learning-curve'),
    path('learning/review/due/', ReviewDueView.as_view(), name='review-due'),
    path('learning/review/practice/', ReviewPracticeView.as_view(), name='review-practice'),
    path('io/import/', ImportNotesView.as_view(), name='io-import'),
    path('io/export/', ExportQuestionsView.as_view(), name='io-export'),
    path('', include(router.urls)),  
]