# Generated by Django 4.0.4 on 2022-05-15 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0006_alter_todolog_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='todolog',
            old_name='id',
            new_name='unique_id',
        ),
        migrations.RemoveField(
            model_name='todoitem',
            name='id',
        ),
        migrations.AddField(
            model_name='todoitem',
            name='unique_id',
            field=models.AutoField(primary_key=True, serialize=False),
            preserve_default=False,
        ),
    ]
