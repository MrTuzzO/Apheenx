from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('video', '0009_alter_video_trailer'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='videoorder',
            index=models.Index(fields=['payment_status', 'created_at'], name='videoord_pay_created_idx'),
        ),
        migrations.AddIndex(
            model_name='videoorder',
            index=models.Index(fields=['payment_status', 'video'], name='videoord_pay_video_idx'),
        ),
    ]
