# Generated by Django 3.2.16 on 2023-01-21 21:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_customuser_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customuser',
            old_name='is_subscribed',
            new_name='subscribers',
        ),
    ]