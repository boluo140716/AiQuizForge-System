import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0014_knowledge_points'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserKPMastery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('p_mastery', models.FloatField(default=0.3, verbose_name='当前掌握概率')),
                ('p_init', models.FloatField(default=0.3, verbose_name='初始掌握概率')),
                ('p_transit', models.FloatField(default=0.15, verbose_name='学习转移概率')),
                ('p_slip', models.FloatField(default=0.1, verbose_name='失误概率')),
                ('p_guess', models.FloatField(default=0.25, verbose_name='猜测概率')),
                ('attempts', models.IntegerField(default=0, verbose_name='作答次数')),
                ('correct', models.IntegerField(default=0, verbose_name='答对次数')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('kp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='masteries', to='notes.knowledgepoint', verbose_name='知识点')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kp_masteries', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '知识点掌握度',
                'verbose_name_plural': '知识点掌握度',
                'db_table': 'user_kp_mastery',
                'constraints': [models.UniqueConstraint(fields=('user', 'kp'), name='uq_ukm_user_kp')],
                'indexes': [models.Index(fields=['user'], name='idx_ukm_user')],
            },
        ),
    ]
