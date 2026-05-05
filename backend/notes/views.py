from rest_framework import viewsets,permissions,filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import Note,Notebook
from .serializers import NoteListSerializer,NotebookSerializer,NoteCreateUpdateSerializer,NoteDetailSerializer


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
    
    def get_serializer_class(self):
        if self.action=='list':
            return NoteListSerializer
        elif self.action in ['create','update','partial_update']:
            return NoteCreateUpdateSerializer
        return NoteDetailSerializer

    def perform_create(self, serializer):
        # 自动绑定用户
        serializer.save(user=self.request.user)