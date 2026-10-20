import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0013_quiz_progress'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='知识点名称')),
                ('description', models.TextField(blank=True, default='', verbose_name='知识点说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('notebook', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_points', to='notes.notebook', verbose_name='所属笔记本')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_points', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '知识点',
                'verbose_name_plural': '知识点',
                'db_table': 'knowledge_points',
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('user', 'notebook', 'name'), name='uq_kp_user_nb_name')],
            },
        ),
        migrations.CreateModel(
            name='NoteKnowledgePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='note_links', to='notes.knowledgepoint', verbose_name='知识点')),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kp_links', to='notes.note', verbose_name='笔记')),
            ],
            options={
                'verbose_name': '笔记-知识点',
                'verbose_name_plural': '笔记-知识点',
                'db_table': 'note_knowledge_point',
                'constraints': [models.UniqueConstraint(fields=('note', 'kp'), name='uq_note_kp')],
            },
        ),
        migrations.CreateModel(
            name='QuestionKnowledgePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.FloatField(default=1.0, verbose_name='权重')),
                ('kp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_links', to='notes.knowledgepoint', verbose_name='知识点')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kp_links', to='notes.question', verbose_name='题目')),
            ],
            options={
                'verbose_name': '题目-知识点',
                'verbose_name_plural': '题目-知识点',
                'db_table': 'question_knowledge_point',
                'constraints': [models.UniqueConstraint(fields=('question', 'kp'), name='uq_q_kp')],
            },
        ),
    ]
