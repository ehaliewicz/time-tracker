from django.urls import path, include
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from . import settings
from django.conf.urls.static import static
from django.contrib.auth import views
from todo.forms import UserLoginForm


admin.autodiscover()


import todo.views

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/

urlpatterns = [
    path("update_todo_log/<int:log_id>", todo.views.update_todo_log, name="update todo log"),
    path("new_todo_log/", todo.views.new_todo_log, name="new todo log"),
    path("delete_todo_log/<int:log_id>", todo.views.delete_todo_log, name="delete todo log"),

    path("update_todo_item/<int:item_id>", todo.views.update_todo_item, name="update todo item"),
    path("new_todo_item/", todo.views.new_todo_item, name="new todo item"),
    path("delete_todo_item/<int:item_id>", todo.views.delete_todo_item, name="delete todo item"),

    path("day/<str:date>", todo.views.date_todos, name="date todos"),
    path("day/<str:date>/", todo.views.date_todos, name="date todos"),
    path("today/", todo.views.todays_todos, name="todays todos"),
    path("today_jinja/", todo.views.todays_todos_jinja, name="todays todos jinja ver."),
    
    path("todo_list/", todo.views.todo_list, name="todo list"),
    path("", todo.views.redirect_to_today, name=""),

    path("import_log_file/", todo.views.import_logs_for_date, name="import logs for date"),
    #path("import_todo_file", todo.views.import_todo_file, name="import todo file"),

    path("logs_by_tag/<str:tag>", todo.views.list_todo_logs_for_tag, name="list todos for tag"),

    path("start_timer/<int:log_id>", todo.views.start_timer, name="start timer for log"),
    path("pause_timer/<int:log_id>", todo.views.pause_timer, name="pause timer for log"),
    path("resume_timer/<int:log_id>", todo.views.resume_timer, name="resume timer for log"),
    path("stop_timer/<int:log_id>", todo.views.stop_timer, name="stop timer for log"),
    
    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url('img/favicon.ico'))),

    path("__debug__/", include("debug_toolbar.urls")),


    path("admin/", admin.site.urls, name="admin page"),
    path("register/", todo.views.register, name="create new user"),

    
    path('accounts/profile/', RedirectView.as_view(url='/today')), #staticfiles_storage.url('img/favicon.ico'))),
    
        
    path('accounts/login/',
     views.LoginView.as_view(
         authentication_form=UserLoginForm
     ),
         name="login user"
    ),

    path('accounts/', include("django.contrib.auth.urls")), # <-- added
    
]
