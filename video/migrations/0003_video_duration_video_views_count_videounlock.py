from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('video', '0002_video_income'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='duration',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Video duration in seconds'
            ),
        ),
        migrations.AddField(
            model_name='video',
            name='views_count',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
        migrations.CreateModel(
            name='VideoUnlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_reference', models.CharField(blank=True, max_length=255)),
                ('unlocked_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='unlocked_videos',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('video', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='unlocks',
                    to='video.video',
                )),
            ],
            options={
                'ordering': ['-unlocked_at'],
                'unique_together': {('user', 'video')},
            },
        ),
    ]
