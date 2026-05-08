from django.db import models
from django.conf import settings

class Notebook(models.Model):
    name=models.CharField(max_length=255,verbose_name="笔记本名称")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notebooks",verbose_name="用户")
    created_at=models.DateTimeField(auto_now_add=True,verbose_name="创建时间")

    class Meta:
        db_table="notebooks"
        verbose_name="笔记本"
        verbose_name_plural="笔记本"
        ordering=["-created_at"]
        unique_together=['name','user']

    def __str__(self):
        return f'{self.name} ({self.user.username})'


class Note(models.Model):
    title=models.CharField(max_length=255,verbose_name="笔记标题")
    content_md=models.TextField(verbose_name='笔记内容(Markdown格式)')#Markdown格式的笔记内容
    content_plain=models.TextField(verbose_name='笔记内容（纯文本格式）')#纯文本格式的笔记内容
    notebook=models.ForeignKey(Notebook,on_delete=models.CASCADE,related_name="notes",verbose_name="所属笔记本")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notes",verbose_name="用户")
    tags= models.JSONField(default=dict,blank=True,verbose_name="标签")
    created_at=models.DateTimeField(auto_now_add=True,verbose_name="创建时间")
    updated_at=models.DateTimeField(auto_now=True,verbose_name="更新时间")

    class Meta:
        db_table = 'notes'
        verbose_name = '笔记'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return self.title
    

class Quiz(models.Model):
    '''测验记录'''
    STATUS_CHOICES = (
        ('processing', '生成中'),
        ('completed', '已完成'),
        ('failed', '生成失败'),
    )

    note=models.ForeignKey(Note,on_delete=models.CASCADE,related_name="quizzes",verbose_name="所属笔记")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="quizzes",verbose_name="发起用户")
    status=models.CharField(max_length=255,choices=STATUS_CHOICES,default='processing',verbose_name="状态")
    question_count=models.IntegerField(default=5,verbose_name="问题数量")
    error_message=models.TextField(blank=True,null=True,verbose_name="错误信息")
    created_at=models.DateTimeField(auto_now_add=True,verbose_name="创建时间")

    class Meta:
        db_table = 'quizzes'
        verbose_name = '测验记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.note.title} 的测验 ({self.get_status_display()})'
    
class Question(models.Model):
    '''测验问题'''
    stem=models.CharField(max_length=255,verbose_name="问题干")
    options=models.JSONField(verbose_name="选项")
    answer=models.CharField(max_length=255,verbose_name="答案")
    explanation=models.TextField(blank=True,null=True,verbose_name="解析")
    quiz=models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name="questions",verbose_name="所属测验")

    class Meta:
        db_table = 'questions'
        verbose_name = '测验问题'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.stem[:50]

