# Generated by Django 3.2.16 on 2023-05-06 15:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership_file', '0017_remove_member_has_paid_membership_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membership',
            name='member',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='membership_file.member'),
        ),
    ]
