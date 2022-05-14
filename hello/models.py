from django.db import models


class TodoItem(models.Model):
    description = models.CharField(max_length=1024)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128)


class TodoLog(models.Model):
    description = models.CharField(max_length=1024)
    duration = models.IntegerField()
    tag = models.CharField(max_length=128)
    date = models.DateField()
