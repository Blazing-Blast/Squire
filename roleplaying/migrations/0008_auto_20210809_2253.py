# Generated by Django 2.2.15 on 2021-08-09 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roleplaying', '0007_auto_20210809_2250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roleplayingitem',
            name='external_file_location',
            field=models.URLField(blank=True, max_length=256, null=True),
        ),
    ]
