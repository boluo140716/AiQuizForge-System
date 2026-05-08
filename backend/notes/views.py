from rest_framework import viewsets,permissions,filters,status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Note,Notebook,Quiz,Question
from .serializers import NoteListSerializer,NotebookSerializer,NoteCreateUpdateSerializer,NoteDetailSerializer,GenerateQuizSerializer,QuizStatusSerializer,QuestionSerializer,QuestionWithAnswerSerializer
from .task import generate_quiz

class NotebookViewSet(viewsets.ModelViewSet):
    serializer_class=NotebookSerializer  
    permission_classes=[permissions.IsAuthenticated] 
    filter_backends=[filters.SearchFilter,filters.OrderingFilter]  # 添加搜索和排序功能
    search_fields=['name']  # 按照笔记名称搜索
    ordering_fields=['created_at','name']

    # 自定义查询集，只返回当前用户创建的笔记
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)
    
    # 创建笔记时，自动添加当前用户
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class NoteViewSet(viewsets.ModelViewSet):
    permission_class=[permissions.IsAuthenticated] 
    pagination_class=NotePagination
    filter_backends=[DjangoFilterBackend,filters.SearchFilter,filters.OrderingFilter]
    filterset_fields=['notebook']  # 按照笔记本过滤
    search_fields=['title','content_plain']  # 按照标题和内容搜索
    ordering_fields=['created_at','updated_at','title']

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user).select_related('notebook')  
    
    # 自定义序列化器，根据操作返回不同的序列化器
    def get_serializer_class(self):
        if self.action=='list':
            return NoteListSerializer
        elif self.action in ['create','update','partial_update']:
            return NoteCreateUpdateSerializer
        return NoteDetailSerializer

    def perform_create(self, serializer):
        # 自动绑定用户
        serializer.save(user=self.request.user)

class QuizViewSet(viewsets.GenericViewSet):
    serializer_class = QuizStatusSerializer  # 设置默认序列化器，避免错误
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='generate/(?P<note_id>\\d+)')
    def generate(self, request, note_id=None):
        # 校验笔记是否存在且属于当前用户
        try:
            note = Note.objects.get(id=note_id, user=request.user)
        except Note.DoesNotExist:
            return Response({'detail': '笔记不存在'}, status=status.HTTP_404_NOT_FOUND)
        # 校验输入参数
        serializer = GenerateQuizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question_count = serializer.validated_data['question_count']
        #检查笔记内容是否足够长
        if not note.content_plain or len(note.content_plain) < 20:
            return Response(
                {'detail': '笔记内容太短，至少需要20个字符才能生成测验'},
                status=status.HTTP_400_BAD_REQUEST
            )
         # 创建 Quiz 记录
        quiz = Quiz.objects.create(
            note=note,
            user=request.user,
            question_count=question_count,
            status='processing'
        )
        # 提交异步任务
        generate_quiz.delay(quiz.id)

        return Response({
            'quiz_id': quiz.id,
            'status': 'processing',
            'message': '测验正在生成中，请稍候...'
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'], url_path='status')
    def status(self, request, pk=None):
        """查询测验生成状态"""
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        serializer = QuizStatusSerializer(quiz)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='questions')
    def questions(self, request, pk=None):
        """获取测验的所有题目（答题用，不返回答案）"""
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        if quiz.status != 'completed':
            return Response({'detail': '测验尚未生成完毕'}, status=status.HTTP_400_BAD_REQUEST)

        questions = quiz.questions.all()
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
        
