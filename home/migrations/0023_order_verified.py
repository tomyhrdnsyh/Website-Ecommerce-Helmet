# Generated by Django 4.1.5 on 2023-02-09 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0022_customuser_address_customuser_city_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]
