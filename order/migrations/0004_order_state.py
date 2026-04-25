from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_rename_status_order_order_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='state',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
