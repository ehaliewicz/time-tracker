# Generated by Django 4.0.4 on 2022-05-14 05:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0003_delete_greeting'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='todoitem',
            name='name',
        ),
        migrations.RemoveField(
            model_name='todolog',
            name='name',
        ),
    ]
