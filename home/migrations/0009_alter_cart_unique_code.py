# Generated by Django 4.1.4 on 2022-12-25 03:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0008_alter_cart_status_alter_cart_unique_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='unique_code',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]