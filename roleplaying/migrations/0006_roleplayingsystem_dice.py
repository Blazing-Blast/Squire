# Generated by Django 2.2.8 on 2021-08-08 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roleplaying', '0005_auto_20210808_1347'),
    ]

    operations = [
        migrations.AddField(
            model_name='roleplayingsystem',
            name='dice',
            field=models.TextField(blank=True, max_length=32, null=True),
        ),
    ]
