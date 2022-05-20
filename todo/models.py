from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User 

class TodoItem(models.Model):
    unique_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=1024, null=False, blank=False)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128, null=False, blank=True, default="")


class TodoLog(models.Model):
    unique_id = models.AutoField(primary_key=True)
    completion = models.BooleanField(default=False)
    description = models.CharField(max_length=1024, null=False, blank=False)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128, null=False, blank=True, default="")
    date = models.DateField()
    #user = models.ForeignKey(User, null=False, on_delete=models.PROTECT)
    
    class Meta:
        indexes = [
            # query all logs for today
            # query all completed logs for this week
            # query all completed logs for all time
            models.Index(fields=['date', 'completion']),
            models.Index(fields=['completion']),
            models.Index(fields=['tag']),
            models.Index(fields=['date', 'duration', 'unique_id'])
        ]
    
class TodoItemForm(ModelForm):
    class Meta:
        model = TodoItem
        fields = ('description', 'duration', 'tag')

class TodoLogForm(ModelForm):
    class Meta:
        model = TodoLog
        fields = ('completion','description', 'duration', 'tag', 'date')

    
