# Generated by Django 4.0.4 on 2022-05-20 16:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0024_alter_todoitem_tag_alter_todolog_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActiveTimer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started', models.DateTimeField(auto_now_add=True)),
                ('linked_todo_log', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='todo.todolog', unique=True)),
            ],
        ),
    ]
