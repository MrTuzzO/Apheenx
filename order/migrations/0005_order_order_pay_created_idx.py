from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0004_order_state'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['payment_status', 'created_at'], name='order_pay_created_idx'),
        ),
    ]
