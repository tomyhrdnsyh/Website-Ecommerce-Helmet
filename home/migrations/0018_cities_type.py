# Generated by Django 4.1.4 on 2023-01-02 14:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0017_merge_20230102_2115'),
    ]

    operations = [
        migrations.AddField(
            model_name='cities',
            name='type',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
