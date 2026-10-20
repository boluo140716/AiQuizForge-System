import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0015_user_kp_mastery'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='origin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='copies', to='notes.question', verbose_name='原始题目'),
        ),
        migrations.CreateModel(
            name='ReviewSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ease_factor', models.FloatField(default=2.5, verbose_name='难度因子')),
                ('interval_days', models.IntegerField(default=0, verbose_name='间隔天数')),
                ('repetitions', models.IntegerField(default=0, verbose_name='连续答对次数')),
                ('lapses', models.IntegerField(default=0, verbose_name='遗忘次数')),
                ('due_at', models.DateTimeField(verbose_name='下次复习时间')),
                ('last_reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='上次复习时间')),
                ('kp', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_schedules', to='notes.knowledgepoint', verbose_name='知识点')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_schedules', to='notes.question', verbose_name='题目')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_schedules', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '复习排程',
                'verbose_name_plural': '复习排程',
                'db_table': 'review_schedule',
                'ordering': ['due_at'],
                'constraints': [models.UniqueConstraint(fields=('user', 'question'), name='uq_review_user_question')],
                'indexes': [models.Index(fields=['user', 'due_at'], name='idx_review_user_due')],
            },
        ),
    ]
