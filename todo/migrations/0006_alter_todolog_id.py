# Generated by Django 4.0.4 on 2022-05-15 05:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0005_todolog_completion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todolog',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
