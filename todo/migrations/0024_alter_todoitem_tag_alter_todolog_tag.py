# Generated by Django 4.0.4 on 2022-05-19 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0023_remove_todolog_todo_todolo_date_478d97_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todoitem',
            name='tag',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AlterField(
            model_name='todolog',
            name='tag',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
