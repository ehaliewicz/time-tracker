from django.db import models
from django.forms import ModelForm

class TodoItem(models.Model):
    unique_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=1024)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128)


class TodoLog(models.Model):
    unique_id = models.AutoField(primary_key=True)
    completion = models.BooleanField(default=False)
    description = models.CharField(max_length=1024)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128)
    date = models.DateField()

class TodoItemForm(ModelForm):
    class Meta:
        model = TodoItem
        fields = ('description', 'duration', 'tag')

class TodoLogForm(ModelForm):
    class Meta:
        model = TodoLog
        fields = '__all__'