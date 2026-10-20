from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0012_alter_failedtask_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='progress',
            field=models.JSONField(blank=True, default=dict, verbose_name='生成进度'),
        ),
    ]
