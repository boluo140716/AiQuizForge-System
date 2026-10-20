from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0010_quiz_heartbeat'),
    ]

    operations = [
        migrations.CreateModel(
            name='FailedTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255, verbose_name='任务名')),
                ('task_id', models.CharField(blank=True, max_length=64, null=True, verbose_name='任务ID')),
                ('args', models.JSONField(blank=True, default=list, verbose_name='位置参数')),
                ('kwargs', models.JSONField(blank=True, default=dict, verbose_name='关键字参数')),
                ('error', models.TextField(blank=True, null=True, verbose_name='错误信息')),
                ('traceback', models.TextField(blank=True, null=True, verbose_name='堆栈')),
                ('retries', models.IntegerField(default=0, verbose_name='已重试次数')),
                ('status', models.CharField(default='pending', max_length=16, verbose_name='状态')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '失败任务',
                'verbose_name_plural': '失败任务',
                'db_table': 'failed_task',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['status', 'created_at'], name='idx_ft_status_created')],
            },
        ),
    ]
