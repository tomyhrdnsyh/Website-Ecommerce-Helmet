# Generated by Django 4.1.4 on 2023-01-02 14:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0018_cities_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cities',
            name='type',
        ),
    ]
