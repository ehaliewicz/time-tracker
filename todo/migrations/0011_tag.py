# Generated by Django 4.0.4 on 2022-05-17 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0010_alter_todoitem_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('name', models.CharField(max_length=128, primary_key=True, serialize=False)),
            ],
        ),
    ]
