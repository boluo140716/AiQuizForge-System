from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0009_quiz_idempotency_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='heartbeat_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='任务心跳时间'),
        ),
        migrations.AddIndex(
            model_name='quiz',
            index=models.Index(fields=['status', 'heartbeat_at'], name='idx_quiz_status_hb'),
        ),
    ]
