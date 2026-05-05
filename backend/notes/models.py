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