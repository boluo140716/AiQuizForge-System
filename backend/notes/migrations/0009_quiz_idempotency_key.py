from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0008_fix_email_unique_and_field_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='idempotency_key',
            field=models.CharField(blank=True, max_length=160, null=True, verbose_name='幂等键'),
        ),
        migrations.AddConstraint(
            model_name='quiz',
            constraint=models.UniqueConstraint(fields=('user', 'idempotency_key'), name='uq_quiz_user_idem'),
        ),
    ]
