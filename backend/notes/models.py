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
    tags= models.JSONField(default=list,blank=True,verbose_name="标签")
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
    celery_task_id=models.CharField(max_length=255,null=True,blank=True,verbose_name="Celery任务ID")
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

class QuizAttempt(models.Model):
    '''测验尝试记录'''
    quiz=models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name="attempts",verbose_name="所属测验")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="quiz_attempts",verbose_name="用户")
    score=models.IntegerField(default=0,verbose_name="得分")
    total=models.IntegerField(default=5,verbose_name="总题数")
    correct_rate=models.FloatField(default=0.0,verbose_name="正确率")
    answers_detail=models.JSONField(default=list,verbose_name="答题详情")
    completed_at=models.DateTimeField(auto_now_add=True,verbose_name="完成时间")

    class Meta:
        db_table = 'quiz_attempts'
        verbose_name = '答题记录'
        verbose_name_plural = verbose_name
        ordering = ['-completed_at']
    
    def __str__(self):
        return f'{self.user.username} 的测验,得分：{self.score}/{self.total}'
    
class WrongQuestion(models.Model):
    '''错题记录'''
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="wrong_questions",verbose_name="用户")
    question=models.ForeignKey(Question,on_delete=models.CASCADE,related_name="wrong_questions",verbose_name="错题")
    quiz=models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name="wrong_questions",verbose_name="所属测验")
    user_answer=models.CharField(max_length=255,verbose_name="用户答案")
    wrong_count=models.IntegerField(default=1,verbose_name="错题次数")
    last_wrong_at=models.DateTimeField(auto_now=True,verbose_name="上次错题时间")

    class Meta:
        db_table = 'wrong_questions'
        verbose_name = '错题记录'
        verbose_name_plural = verbose_name
        ordering = ['-last_wrong_at']

    def __str__(self):
        return f'{self.user.username} 的错题记录 ({self.question.stem[:30]})'
