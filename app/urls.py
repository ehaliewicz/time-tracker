from django.urls import path, include
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from . import settings
from django.conf.urls.static import static
from django.contrib.auth import views
from todo.forms import UserLoginForm
import todo.views
import todo.api
admin.autodiscover()




# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/

urlpatterns = [
    path("update_todo_item/<int:item_id>", todo.views.update_todo_item, name="update todo item"),
    path("new_todo_item/", todo.views.new_todo_item, name="new todo item"),
    path("delete_todo_item/<int:item_id>", todo.views.delete_todo_item, name="delete todo item"),

    path("day/<str:date>", todo.views.date_todos, name="date todos"),
    path("day/<str:date>/", todo.views.date_todos, name="date todos"),
    path("today/", todo.views.todays_todos, name="todays todos"),
        
    path("todo_list/", todo.views.todo_list, name="todo list"),
    path("", todo.views.redirect_to_today, name=""),

    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url('img/favicon.ico'))),

    #path("__debug__/", include("debug_toolbar.urls")),

    path("admin/", admin.site.urls, name="admin page"),
    path("register/", todo.views.register, name="create new user"),

    
    path("accounts/profile/", RedirectView.as_view(url='/today')), #staticfiles_storage.url('img/favicon.ico'))),
    
        
    path("accounts/login/",
     views.LoginView.as_view(
         authentication_form=UserLoginForm
     ),
         name="login user"
    ),

    path("accounts/", include("django.contrib.auth.urls")), # <-- added
    
    # api endpoints
    path("api/get_todo_log/<int:log_id>", todo.api.get_todo_log, name="api get todo log"),
    path("api/update_todo_log/<int:log_id>", todo.api.update_todo_log, name="api update todo log"),
    path("api/delete_todo_log/<int:log_id>", todo.api.delete_todo_log, name="api delete todo log"),
    path("api/new_todo_log", todo.api.new_todo_log, name="api new todo log"),
    
    path("api/stats_for_day/<str:date>", todo.api.stats_for_day, name="api stats"),
    path("api/todo_logs_for_day/<str:date>", todo.api.todo_logs_for_day, name="api logs for day"),
    
    path("api/get_timer/<str:date>", todo.api.get_timer, name="api get timer"),
    path("api/start_timer/<int:log_id>", todo.api.start_timer, name="api start timer for log"),
    path("api/pause_timer/<int:log_id>", todo.api.pause_timer, name="api pause timer for log"),
    path("api/resume_timer/<int:log_id>", todo.api.resume_timer, name="resume timer for log"),
    path("api/stop_timer/<int:log_id>", todo.api.stop_timer, name="api stop timer for log"),
    
]
