from django.urls import path, include

from django.contrib import admin

admin.autodiscover()

import hello.views

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/

urlpatterns = [
    path("today/", hello.views.todays_todos, name="todays todos"),
    path("todo_list/", hello.views.todo_list, name="todo list"),
    path("", hello.views.redirect_to_today, name="")
]
