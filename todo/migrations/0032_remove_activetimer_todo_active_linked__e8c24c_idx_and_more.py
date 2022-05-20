# Generated by Django 4.0.4 on 2022-05-20 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0031_activetimer_user_stats_user_todoitem_user_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='activetimer',
            name='todo_active_linked__e8c24c_idx',
        ),
        migrations.RemoveIndex(
            model_name='todolog',
            name='todo_todolo_tag_3deafb_idx',
        ),
        migrations.RemoveIndex(
            model_name='todolog',
            name='todo_todolo_date_3dd119_idx',
        ),
        migrations.RemoveIndex(
            model_name='todolog',
            name='todo_todolo_complet_d33c66_idx',
        ),
        migrations.RemoveIndex(
            model_name='todolog',
            name='todo_todolo_date_202e91_idx',
        ),
        migrations.AddIndex(
            model_name='activetimer',
            index=models.Index(fields=['user_id', 'linked_todo_log'], name='todo_active_user_id_59a3fc_idx'),
        ),
        migrations.AddIndex(
            model_name='stats',
            index=models.Index(fields=['user_id', 'date'], name='todo_stats_user_id_7dec26_idx'),
        ),
        migrations.AddIndex(
            model_name='todoitem',
            index=models.Index(fields=['user_id'], name='todo_todoit_user_id_ba3e28_idx'),
        ),
        migrations.AddIndex(
            model_name='todolog',
            index=models.Index(fields=['user_id', 'date', 'completion'], name='todo_todolo_user_id_ed7404_idx'),
        ),
        migrations.AddIndex(
            model_name='todolog',
            index=models.Index(fields=['user_id', 'completion'], name='todo_todolo_user_id_b41b02_idx'),
        ),
        migrations.AddIndex(
            model_name='todolog',
            index=models.Index(fields=['user_id', 'tag'], name='todo_todolo_user_id_245287_idx'),
        ),
        migrations.AddIndex(
            model_name='todolog',
            index=models.Index(fields=['user_id', 'date', 'duration', 'unique_id'], name='todo_todolo_user_id_bf5caf_idx'),
        ),
    ]
