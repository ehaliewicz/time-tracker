# Generated by Django 4.0.4 on 2022-05-18 02:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0015_alter_todoitem_tag_ref_alter_todolog_tag_ref'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='todoitem',
            name='tag_ref',
        ),
        migrations.RemoveField(
            model_name='todolog',
            name='tag_ref',
        ),
    ]
