from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from django.contrib.auth.models import User
import logging

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




class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
    
    username = UsernameField(widget=forms.TextInput(
        attrs={'placeholder': ''}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'placeholder': '',
        }
    ))
    timezone_name = forms.CharField(widget=forms.TextInput(
        attrs={'placeholder': '', 'id': 'timezone-input'}
    ))



def add_login_timezone_to_session_middleware(get_response):

    def middleware(request):

        # before other middleware/view/templates
        response = get_response(request)
        # after other middleware/view/templates

        if request.path == '/accounts/login/' and request.method == 'POST' and request.user.is_authenticated:
            request.session['tz_name'] = request.POST['timezone_name']
            
                
        return response

    return middleware
