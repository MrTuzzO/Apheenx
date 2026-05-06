from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("video", "0010_videoorder_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="videoorder",
            name="paypal_approval_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="videoorder",
            name="paypal_order_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
