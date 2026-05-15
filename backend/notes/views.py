from rest_framework import viewsets,permissions,filters,status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle
from config.throttles import GenerateQuizRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from .models import Note,Notebook,Quiz,Question,WrongQuestion,QuizAttempt
from .serializers import (NoteListSerializer,NotebookSerializer,NoteCreateUpdateSerializer,
                          NoteDetailSerializer,GenerateQuizSerializer,QuizListSerializer,QuizStatusSerializer,
                          QuestionSerializer,SubmitAnswerSerializer,QuizAttemptSerializer,WrongQuestionSerializer,QuestionWithAnswerSerializer)
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
    permission_classes=[permissions.IsAuthenticated]
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

#测验视图
class QuizViewSet(viewsets.GenericViewSet):
    serializer_class = QuizStatusSerializer  # 设置默认序列化器，避免错误
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """获取用户的所有测验列表（含答题统计）"""
        quizzes = Quiz.objects.filter(user=request.user).select_related('note').order_by('-created_at')

        data = []
        for q in quizzes:
            attempts = list(QuizAttempt.objects.filter(quiz=q).order_by('-completed_at'))
            q._attempt_count = len(attempts)
            q._best_score = max((a.score for a in attempts), default=0)
            q._last_attempt_at = attempts[0].completed_at if attempts else None
            data.append(QuizListSerializer(q).data)
        return Response(data)

    # 生成测验接口
    @action(detail=False, methods=['post'], url_path='generate/(?P<note_id>\\d+)',throttle_classes=[GenerateQuizRateThrottle])
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
        task = generate_quiz.delay(quiz.id)
        quiz.celery_task_id = task.id
        quiz.save(update_fields=['celery_task_id'])

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

    @action(detail=True, methods=['post'], url_path='cancel-delete')
    def cancel_delete(self, request, pk=None):
        """取消并删除生成中的测验"""
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        if quiz.status != 'processing':
            return Response({'detail': '只能取消生成中的测验'}, status=status.HTTP_400_BAD_REQUEST)

        # 撤销 Celery 异步任务
        if quiz.celery_task_id:
            try:
                from config.celery import app
                app.control.revoke(quiz.celery_task_id, terminate=False)
            except Exception:
                pass

        # 级联删除测验及其所有关联数据（题目、答题记录、错题）
        quiz.delete()

        return Response({'status': 'deleted', 'message': '已取消并删除测验'})

    @action(detail=True, methods=['post'], url_path='delete')
    def delete_quiz(self, request, pk=None):
        """删除测验（支持已完成和生成失败的测验）"""
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 如果是生成中的测验，尝试撤销 Celery 任务
        if quiz.celery_task_id:
            try:
                from config.celery import app
                app.control.revoke(quiz.celery_task_id, terminate=False)
            except Exception:
                pass

        # 级联删除测验及其所有关联数据（题目、答题记录、错题）
        quiz.delete()

        return Response({'status': 'deleted', 'message': '已删除测验'})


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
        serializer = QuestionWithAnswerSerializer(questions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='attempt')
    def attempt(self, request, pk=None):
        # 校验测验是否存在且属于当前用户
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        #测验必须生成完毕才能答题
        if quiz.status != 'completed':
            return Response({'detail': '测验尚未生成完毕'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 校验输入答案参数是否符合要求
        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data['answers']

        #获取所有题目
        questions = Question.objects.filter(quiz=quiz)
        question_map={q.id:q for q in questions}

        #验证提交的question_id都属于本次测验
        submitted_ids={a['question_id'] for a in answers}
        valid_ids=set(question_map.keys())
        if not submitted_ids.issubset(valid_ids):
            return Response({'detail': '提交的题目ID包含不存在的题目'}, status=status.HTTP_400_BAD_REQUEST)
        
        #逐个验证答案
        score = 0
        total = len(questions)
        answers_detail = []

        for answer_item in answers:
            qid=answer_item['question_id']
            selected=answer_item['selected']
            question=question_map[qid]
            correct=question.answer
            is_right=(selected.strip().upper()==correct.strip().upper())

            if is_right:
                score+=1
            else:
                wrong_q,created=WrongQuestion.objects.get_or_create(
                    user=request.user,
                    question=question,
                    defaults={
                        'quiz':quiz,
                        'user_answer':selected,
                        'wrong_count':1
                    }
                )
                if not created:
                    # 之前就错过，更新错误次数和最后错误时间
                    wrong_q.wrong_count += 1
                    wrong_q.user_answer = selected
                    wrong_q.quiz = quiz
                    wrong_q.save()
            
            answers_detail.append({
                'question_id': qid,
                'stem': question.stem,
                'options': question.options,
                'selected': selected,
                'correct': correct,
                'is_right': is_right,
                'explanation': question.explanation if not is_right else None
            })
        #创建答题记录
        correct_rate=score/total if total>0 else 0.0
        attempt_record=QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            score=score,
            total=total,
            correct_rate=round(correct_rate,2), #保留两位小数
            answers_detail=answers_detail
        )

        return Response({
            'attempt_id': attempt_record.id,
            'score': score,
            'total': total,
            'correct_rate': round(correct_rate, 2),
            'answers_detail': answers_detail
        }, status=status.HTTP_200_OK)

    

    #获取所有答题记录
    @action(detail=True, methods=['get'], url_path='attempts')
    def attempts(self, request, pk=None):

        try:    
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)

        attempts = QuizAttempt.objects.filter(quiz=quiz,user=request.user)
        serializer = QuizAttemptSerializer(attempts, many=True)
        return Response(serializer.data)
    
     #测验回顾
    @action(detail=True, methods=['get'], url_path='review')
    def review(self, request, pk=None):
        try:
            quiz=Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        if quiz.status!='completed':
            return Response({'detail': '测验未完成'}, status=status.HTTP_400_BAD_REQUEST)
        #获取题目数据
        questions=quiz.questions.all()
        question_data=QuestionWithAnswerSerializer(questions, many=True).data

        #最近一次答题记录
        last_attempt=QuizAttempt.objects.filter(quiz=quiz,user=request.user).order_by('-completed_at').first()
        attempt_data=QuizAttemptSerializer(last_attempt).data if last_attempt else None

        return Response({
            'quiz_id': quiz.id,
            'note_title': quiz.note.title,
            'question_count': quiz.question_count,
            'questions': question_data,
            'last_attempt': attempt_data
        })
    
#错题视图
class WrongQuestionViewSet(viewsets.GenericViewSet):
    serializer_class = WrongQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    #获取错题列表
    def get_queryset(self):
        return WrongQuestion.objects.filter(user=self.request.user).select_related('question','quiz','quiz__note')
    
    #获取当前用户错题
    @action(detail=False, methods=['get'], url_path='list')
    def wrong_list(self, request):
        queryset=self.get_queryset()
        #可选筛选，按测验
        quiz_id=request.query_params.get('quiz_id')
        if quiz_id:
            queryset=queryset.filter(quiz_id=quiz_id)

        #可选筛选，按笔记
        notebook_id=request.query_params.get('notebook_id')
        if notebook_id:
            queryset=queryset.filter(quiz__note__notebook_id=notebook_id)

        #可选筛选，按标签
        tag=request.query_params.get('tag')
        if tag:
            queryset=queryset.filter(quiz__note__tags__contains=tag)

        #按最后错误时间排序
        queryset=queryset.order_by('-last_wrong_at')

        #分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    #错题重练接口
    @action(detail=False, methods=['post'], url_path='re-practice')
    def re_practice(self, request):
        limit=int(request.data.get('limit', 5)) #默认5道
        quiz_id=request.data.get('quiz_id')
        notebook_id=request.data.get('notebook_id')

        queryset=self.get_queryset()
        #可选筛选，按测验
        if quiz_id:
            queryset=queryset.filter(quiz_id=quiz_id)

        #可选筛选，按笔记
        if notebook_id:
            queryset=queryset.filter(quiz__note__notebook_id=notebook_id)

        #可选筛选，按标签
        tag=request.data.get('tag')
        if tag:
            queryset=queryset.filter(quiz__note__tags__contains=tag)

        #按错误次数降序排序
        queryset=queryset.order_by('-wrong_count')
        #获取去重后的题目ID
        question_ids=queryset.values_list('question_id', flat=True).distinct()[:limit]
        if not question_ids:
            return Response({'detail': '错题本为空'}, status=status.HTTP_404_NOT_FOUND)
        # 创建一个临时测验记录
        first_wrong = WrongQuestion.objects.filter(
            user=request.user, question_id__in=question_ids
        ).first()
        temp_quiz = Quiz.objects.create(
            note=first_wrong.quiz.note,
            user=request.user,
            question_count=len(question_ids),
            status='completed'
        )

        # 复制题目到临时测验，保留原题不变
        original_questions = Question.objects.filter(id__in=question_ids)
        new_questions = []
        for q in original_questions:
            new_q = Question.objects.create(
                stem=q.stem,
                options=q.options,
                answer=q.answer,
                explanation=q.explanation,
                quiz=temp_quiz
            )
            new_questions.append(new_q)

        serializer = QuestionWithAnswerSerializer(new_questions, many=True)
        return Response({
            'practice_quiz_id': temp_quiz.id,
            'questions': serializer.data
        }, status=status.HTTP_200_OK)
    
    #获取所有错题关联的标签
    @action(detail=False, methods=['get'], url_path='tags')
    def tags(self, request):
        queryset = self.get_queryset().filter(quiz__note__tags__isnull=False)
        tag_set = set()
        for wq in queryset:
            tags = wq.quiz.note.tags
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str) and t.strip():
                        tag_set.add(t.strip())
        return Response({'tags': sorted(tag_set)})

    #错题移除接口
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove(self, request, pk=None):
        try:
            wrong_q=WrongQuestion.objects.get(id=pk, user=request.user)
        except WrongQuestion.DoesNotExist:
            return Response({'detail': '错题不存在'}, status=status.HTTP_404_NOT_FOUND)
        wrong_q.delete()
        return Response(
            {'detail': '错题已移除'}
            ,status=status.HTTP_200_OK
        )