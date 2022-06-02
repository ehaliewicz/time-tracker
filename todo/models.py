from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

class TodoItem(models.Model):
    unique_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=1024, null=False, blank=False)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128, null=False, blank=True, default="")

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        indexes = [
            models.Index(fields=['user_id'])
        ]

    
class TodoLog(models.Model):
    unique_id = models.AutoField(primary_key=True)
    completion = models.BooleanField(default=False)
    description = models.CharField(max_length=1024, null=False, blank=False)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128, null=False, blank=True, default="")
    date = models.DateField()
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    
    class Meta:
        indexes = [
            # query all logs for today
            # query all completed logs for this week
            # query all completed logs for all time
            models.Index(fields=['user_id','date', 'completion']),
            models.Index(fields=['user_id','completion']),
            models.Index(fields=['user_id','tag']),
            models.Index(fields=['user_id','date', 'duration', 'unique_id'])
            
        ]

        
class ActiveTimer(models.Model):
    started = models.DateTimeField(auto_now_add=True, null=False)
    linked_todo_log = models.OneToOneField(TodoLog, on_delete=models.PROTECT)
    paused = models.DateTimeField(null=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=False, unique=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user_id','linked_todo_log']),
        ]

class Stats(models.Model):
    date = models.DateField(null=False, primary_key=True)
    stats = models.JSONField(null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['date', 'user_id' ]),
        ]
