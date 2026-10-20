import csv
import os
import uuid
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets,permissions,filters,status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from config.throttles import GenerateQuizRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Note, Notebook, Quiz, Question, WrongQuestion, QuizAttempt,
    UserKPMastery, QuestionKnowledgePoint, ReviewSchedule,
)
from django.db.models import Count
from .mastery import update_mastery
from .srs import update_review_schedule
from .utils import md_to_plain_text
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
        # 用 annotate 一次算出笔记数，避免序列化时逐本 count（N+1）
        return Notebook.objects.filter(user=self.request.user).annotate(_note_count=Count('notes')).order_by('-created_at')
    
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
        quizzes = (
            Quiz.objects.filter(user=request.user)
            .select_related('note')
            .prefetch_related('attempts')
            .order_by('-created_at')
        )

        data = []
        for q in quizzes:
            attempts = list(q.attempts.all())  # 已被 prefetch，不再逐条查库
            q._attempt_count = len(attempts)
            q._best_score = max((a.score for a in attempts), default=0)
            q._last_attempt_at = attempts[0].completed_at if attempts else None
            data.append(QuizListSerializer(q).data)
        return Response(data)

    # 生成测验接口（支持幂等：同一 Idempotency-Key 的重复请求只生成一个测验）
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
        if not note.content_plain or len(note.content_plain) < 50:
            return Response(
                {'detail': '笔记内容太短，至少需要50个字符才能生成测验'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ===== 幂等处理 =====
        # 前端每次"生成"会带一个唯一编号 Idempotency-Key；相同编号的重复请求
        # （手滑连点、网络重试）不会重复创建测验，而是返回已有测验。
        idem_key = (request.headers.get('Idempotency-Key') or '')[:160]
        idem_cache_key = f'idem:quiz:{request.user.id}:{idem_key}' if idem_key else None

        if idem_key:
            existing = self._find_idempotent_quiz(request.user, idem_key, idem_cache_key)
            if existing is not None:
                return Response({
                    'quiz_id': existing.id,
                    'status': existing.status,
                    'message': '检测到重复请求，返回已有测验',
                    'duplicated': True,
                }, status=status.HTTP_202_ACCEPTED)

        # 创建 Quiz 记录
        try:
            quiz = Quiz.objects.create(
                note=note,
                user=request.user,
                question_count=question_count,
                status='processing',
                idempotency_key=idem_key or None,
            )
        except IntegrityError:
            # 并发兜底：唯一约束 (user, idempotency_key) 拦下了重复创建
            existing = Quiz.objects.filter(user=request.user, idempotency_key=idem_key).first()
            if existing is not None:
                if idem_cache_key:
                    cache.set(idem_cache_key, existing.id, 86400)
                return Response({
                    'quiz_id': existing.id,
                    'status': existing.status,
                    'message': '检测到重复请求，返回已有测验',
                    'duplicated': True,
                }, status=status.HTTP_202_ACCEPTED)
            raise

        if idem_cache_key:
            cache.set(idem_cache_key, quiz.id, 86400)   # 缓存 24 小时，便于快速判重

        # 生成追踪 ID，用于关联 Django → Celery → FastAPI 调用链
        trace_id = str(uuid.uuid4())[:8]

        # 提交异步任务
        task = generate_quiz.delay(quiz.id, trace_id=trace_id)
        quiz.celery_task_id = task.id
        quiz.save(update_fields=['celery_task_id'])

        return Response({
            'quiz_id': quiz.id,
            'status': 'processing',
            'message': '测验正在生成中，请稍候...'
        }, status=status.HTTP_202_ACCEPTED)

    def _find_idempotent_quiz(self, user, idem_key, idem_cache_key):
        """查找该幂等键对应的已有测验：缓存优先，数据库兜底。"""
        if idem_cache_key:
            cached_id = cache.get(idem_cache_key)
            if cached_id:
                quiz = Quiz.objects.filter(id=cached_id, user=user).first()
                if quiz is not None:
                    return quiz
        quiz = Quiz.objects.filter(user=user, idempotency_key=idem_key).first()
        if quiz is not None and idem_cache_key:
            cache.set(idem_cache_key, quiz.id, 86400)
        return quiz
    
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


    @action(detail=False, methods=['post'], url_path='adaptive')
    def adaptive(self, request):
        """自适应组卷：按知识点掌握度选题，复制成一次练习。"""
        from .adaptive import select_adaptive_questions

        note_id = request.data.get('note_id')
        notebook_id = request.data.get('notebook_id')
        try:
            count = int(request.data.get('count', 5))
        except (TypeError, ValueError):
            count = 5
        count = max(1, min(count, 20))

        note = None
        notebook = None
        if note_id:
            note = Note.objects.filter(id=note_id, user=request.user).first()
            if note is None:
                return Response({'detail': '笔记不存在'}, status=status.HTTP_404_NOT_FOUND)
        if notebook_id:
            notebook = Notebook.objects.filter(id=notebook_id, user=request.user).first()
            if notebook is None:
                return Response({'detail': '笔记本不存在'}, status=status.HTTP_404_NOT_FOUND)

        selected, covered = select_adaptive_questions(
            request.user, note=note, notebook=notebook, count=count
        )
        if not selected:
            return Response(
                {'detail': '暂无可用于自适应练习的题目，请先生成测验'},
                status=status.HTTP_404_NOT_FOUND,
            )

        temp_quiz = Quiz.objects.create(
            note=note,
            user=request.user,
            question_count=len(selected),
            status='completed',
        )
        new_questions = []
        for q in selected:
            new_q = Question.objects.create(
                quiz=temp_quiz,
                stem=q.stem,
                options=q.options,
                answer=q.answer,
                explanation=q.explanation,
                origin_id=q.origin_id or q.id,
            )
            for link in q.kp_links.all():
                QuestionKnowledgePoint.objects.get_or_create(question=new_q, kp=link.kp)
            new_questions.append(new_q)

        serializer = QuestionWithAnswerSerializer(new_questions, many=True)
        return Response({
            'practice_quiz_id': temp_quiz.id,
            'count': len(new_questions),
            'covered_kp_ids': sorted(covered),
            'questions': serializer.data,
        }, status=status.HTTP_200_OK)


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
    
    @action(detail=True, methods=['post'], url_path='attempt')
    @transaction.atomic
    def attempt(self, request, pk=None):
        # 校验测验是否存在且属于当前用户
        try:
            quiz = Quiz.objects.get(id=pk, user=request.user)
        except Quiz.DoesNotExist:
            return Response({'detail': '测验不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        #测验必须生成完毕才能答题
        if quiz.status != 'completed':
            return Response({'detail': '测验尚未生成完毕'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 幂等：同一 Idempotency-Key 的重复提交直接返回上次结果
        idem_key = (request.headers.get('Idempotency-Key') or '')[:128]
        cache_key = f'attempt:{request.user.id}:{quiz.id}:{idem_key}' if idem_key else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return Response(cached, status=status.HTTP_200_OK)

        # 校验输入答案参数是否符合要求
        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data['answers']

        #获取所有题目（预取知识点关联与原始题，避免逐题查库）
        questions = Question.objects.filter(quiz=quiz).select_related('origin').prefetch_related('kp_links__kp')
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

            # 更新该题涉及知识点的掌握度（BKT）
            for link in question.kp_links.all():
                update_mastery(request.user, link.kp, is_right)

            # 更新 SM-2 复习排程（副本题统一记到原始题上）
            schedule_question = question.origin if question.origin_id else question
            update_review_schedule(request.user, schedule_question, is_right)

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

        payload = {
            'attempt_id': attempt_record.id,
            'score': score,
            'total': total,
            'correct_rate': round(correct_rate, 2),
            'answers_detail': answers_detail
        }
        if cache_key:
            cache.set(cache_key, payload, 86400)
        return Response(payload, status=status.HTTP_200_OK)

    

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
        return WrongQuestion.objects.filter(user=self.request.user).select_related('question','quiz','quiz__note','quiz__note__notebook')
    
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
            queryset=queryset.filter(quiz__note__tags__has_key=tag)

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
            queryset=queryset.filter(quiz__note__tags__has_key=tag)

        #按错误次数降序排序
        queryset=queryset.order_by('-wrong_count')
        #获取去重后的题目ID
        question_ids=queryset.values_list('question_id', flat=True).distinct()[:limit]
        if not question_ids:
            return Response({'detail': '错题本为空'}, status=status.HTTP_404_NOT_FOUND)
        # 创建一个临时测验记录
        temp_quiz = Quiz.objects.create(
            note=None,
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
                quiz=temp_quiz,
                origin_id=q.origin_id or q.id,
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


class MasteryView(APIView):
    """GET /api/v1/learning/mastery/ —— 当前用户各知识点的掌握度。"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = (
            UserKPMastery.objects.filter(user=request.user)
            .select_related('kp')
            .order_by('-p_mastery')
        )
        return Response({
            'mastery': [
                {
                    'kp_id': row.kp_id,
                    'kp_name': row.kp.name,
                    'p_mastery': round(row.p_mastery, 4),
                    'attempts': row.attempts,
                    'correct': row.correct,
                }
                for row in rows
            ]
        })


class LearningCurveView(APIView):
    """GET /api/v1/learning/curve/ —— 最近答题记录的正确率曲线。"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = list(
            QuizAttempt.objects.filter(user=request.user)
            .order_by('-completed_at')[:100]
        )
        rows.reverse()
        return Response({
            'curve': [
                {
                    'index': i + 1,
                    'correct_rate': row.correct_rate,
                    'score': row.score,
                    'total': row.total,
                    'completed_at': row.completed_at.isoformat(),
                }
                for i, row in enumerate(rows)
            ]
        })


class ReviewDueView(APIView):
    """GET /api/v1/learning/review/due/ —— 今日到期复习题。"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        rows = (
            ReviewSchedule.objects.filter(user=request.user, due_at__lte=now)
            .select_related('question')
            .order_by('due_at')
        )
        items = [
            {
                'schedule_id': r.id,
                'question_id': r.question_id,
                'stem': r.question.stem,
                'due_at': r.due_at.isoformat(),
                'interval_days': r.interval_days,
                'repetitions': r.repetitions,
                'ease_factor': round(r.ease_factor, 2),
            }
            for r in rows[:50]
        ]
        return Response({'due_count': rows.count(), 'items': items})


class ReviewPracticeView(APIView):
    """POST /api/v1/learning/review/practice/ —— 用到期题目生成一次复习卷。"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        try:
            limit = int(request.data.get('count', 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        rows = list(
            ReviewSchedule.objects.filter(user=request.user, due_at__lte=now)
            .select_related('question')
            .order_by('due_at')[:limit]
        )
        if not rows:
            return Response({'detail': '今日没有需要复习的题目'}, status=status.HTTP_404_NOT_FOUND)

        temp_quiz = Quiz.objects.create(
            note=None, user=request.user,
            question_count=len(rows), status='completed',
        )
        new_questions = []
        for row in rows:
            q = row.question
            new_q = Question.objects.create(
                quiz=temp_quiz,
                stem=q.stem,
                options=q.options,
                answer=q.answer,
                explanation=q.explanation,
                origin_id=q.origin_id or q.id,
            )
            for link in q.kp_links.all():
                QuestionKnowledgePoint.objects.get_or_create(question=new_q, kp=link.kp)
            new_questions.append(new_q)

        serializer = QuestionWithAnswerSerializer(new_questions, many=True)
        return Response({
            'practice_quiz_id': temp_quiz.id,
            'count': len(new_questions),
            'questions': serializer.data,
        }, status=status.HTTP_200_OK)


class ImportNotesView(APIView):
    """POST /api/v1/io/import/ —— 导入 Markdown/TXT 文件为笔记。"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response({'detail': '未收到文件'}, status=status.HTTP_400_BAD_REQUEST)

        notebook_id = request.data.get('notebook_id')
        notebook = None
        if notebook_id:
            notebook = Notebook.objects.filter(id=notebook_id, user=request.user).first()
        if notebook is None:
            notebook, _ = Notebook.objects.get_or_create(name='导入笔记', user=request.user)

        created, skipped = 0, 0
        for f in files:
            name = f.name or ''
            if not name.lower().endswith(('.md', '.markdown', '.txt')):
                skipped += 1
                continue
            raw = f.read().decode('utf-8', errors='ignore')
            if not raw.strip():
                skipped += 1
                continue
            title = os.path.splitext(os.path.basename(name))[0][:255] or '导入笔记'
            Note.objects.create(
                title=title,
                content_md=raw,
                content_plain=md_to_plain_text(raw),
                notebook=notebook,
                user=request.user,
            )
            created += 1

        return Response({'created': created, 'skipped': skipped})


class ExportQuestionsView(APIView):
    """GET /api/v1/io/export/ —— 导出当前用户的题目为 CSV。"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        questions = (
            Question.objects.filter(quiz__user=request.user, quiz__status='completed')
            .prefetch_related('kp_links__kp')
            .order_by('quiz_id', 'id')
        )
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response.write('\ufeff')  # UTF-8 BOM，Excel 打开不乱码
        response['Content-Disposition'] = 'attachment; filename="quizforge_questions.csv"'

        writer = csv.writer(response)
        writer.writerow(['题干', '选项A', '选项B', '选项C', '选项D', '答案', '解析', '知识点'])
        for q in questions:
            options = list(q.options or []) + ['', '', '', '']
            kps = '、'.join(link.kp.name for link in q.kp_links.all())
            writer.writerow([
                q.stem, options[0], options[1], options[2], options[3],
                q.answer, q.explanation or '', kps,
            ])
        return response