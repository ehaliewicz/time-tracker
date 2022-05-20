from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import TodoItem, TodoLog

class TodoItemForm(forms.ModelForm):
    class Meta:
        model = TodoItem
        fields = ('description', 'duration', 'tag')

class TodoLogForm(forms.ModelForm):
    class Meta:
        model = TodoLog
        fields = ('completion','description', 'duration', 'tag', 'date')



class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
