from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View
import dateutil.parser
import logging

from .models import TodoItem, TodoLog, TodoItemForm, TodoLogForm
import datetime

def todoItemToLog(item, date):
    return TodoLog(
        description=item.description,
        duration=item.duration,
        tag=item.tag,
        date=date
    )


def todo_list_or_defaults():
    all_todo_items = TodoItem.objects.all()
    return all_todo_items


def update_todo_log(request, log_id):
    form = TodoLogForm(request.POST)
    if form.is_valid():
        form.instance.unique_id = log_id
        form.instance.save()
    else:
        raise Exception("Error(s) updating todo log {}".format(form.errors))
    
    
    return redirect(request.META.get('HTTP_REFERER'))

def update_todo_item(request, item_id):
    form = TodoItemForm(request.POST)
    if form.is_valid():
        form.instance.unique_id = item_id
        form.instance.save()
    else:
        raise Exception("Error(s) updating todo item {}".format(form.errors))
    
    
    return redirect(request.META.get('HTTP_REFERER'))

def new_todo_log(request):
    form = TodoLogForm(request.POST)
    if form.is_valid():
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo log {}".format(form.errors))
    
    
    return redirect(request.META.get('HTTP_REFERER'))

def new_todo_item(request):
    form = TodoItemForm(request.POST)
    if form.is_valid():
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo item {}".format(form.errors))
    
    
    return redirect(request.META.get('HTTP_REFERER'))



def delete_todo_log(request, log_id):
    todo_log = TodoLog.objects.get(unique_id=log_id)
    todo_log.delete()

    return redirect(request.META.get('HTTP_REFERER'))


def delete_todo_item(request, item_id):
    todo_item = TodoItem.objects.get(unique_id=item_id)
    todo_item.delete()

    return redirect(request.META.get('HTTP_REFERER'))


def calculate_stats(date):
    
    #today = datetime.date.today()
    start_of_week = today-datetime.timedelta(days=7)
    todo_logs_for_today = TodoLog.objects.filter(date=today, completion=True)
    completed_time = sum([log.duration for log in todo_logs_for_today])

    todo_logs_for_week = TodoLog.objects.filter(date__gte=start_of_week, completion=True)
    completed_week = sum([log.duration for log in todo_logs_for_week])

    all_todo_logs = list(TodoLog.objects.all())
    completed_total = sum([log.duration for log in all_todo_logs if log.completion])

    completed_dates = set([log.date for log in all_todo_logs if log.completion])
    

    cur_date = datetime.date.today()
    streak = 0
    while True:
        if not cur_date in completed_dates:
            break
        streak += 1
        cur_date = cur_date - datetime.timedelta(days=1)


    return {
        'completed_time': get_hr_min(completed_time),
        'completed_week_time': get_hr_min(completed_week),
        'total_time': get_hr_min(completed_total),
        'streak': streak
    }


def get_hr_min(m):
    return int(m//60), m%60



def inner_date_todo_logs(request, date, title):

    todo_logs_for_today = TodoLog.objects.filter(date=date).order_by('unique_id')

    if len(todo_logs_for_today) == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = todo_list_or_defaults() #TodoItem.objects.all()

        new_todo_logs = []
        for item in all_todo_items:
            log = todoItemToLog(item, date)
            log.save()
            new_todo_logs.append(log)

        todo_logs_for_today = new_todo_logs

    calced_stats = calculate_stats()

    new_log = TodoLog(date=date)
    form = TodoLogForm(instance=new_log)

    
    return render(request, "day_todo_list.html", {
        "title": "Todo List For {}".format(title),
        "todo_logs": [TodoLogForm(instance=todo_log) for todo_log in todo_logs_for_today],
        "form": form,
        **calced_stats
    })


@csrf_protect
def todays_todos(request):
    date = datetime.date.today()
    title = "Today"
    return inner_date_todo_logs(request, date, title)



@csrf_protect
def date_todos(request, date):
    date = dateutil.parser.parse(date)
    title = "{}/{}/{}".format(date.year, date.month, date.day)
    return inner_date_todo_logs(request, date, title)



class UpdateItemView(View):
    http_method_names = ['post', 'put']
    
    # put is to update
    def put(self, request, log_id):
        form = TodoItemForm(request.POST)
        if form.is_valid():
            form.instance.unique_id = log_id
            form.instance.save()
        else:
            raise Exception("Error(s) updating or creating todo {}".format(form.errors))
    
    
        return redirect(request.META.get('HTTP_REFERER'))

    # post is to create a new item
    def post(self, request):
        form = TodoItemForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            raise Exception("Error creating new todo")

@csrf_protect
def todo_list(request):
    form = TodoItemForm()
    all_todo_items = TodoItem.objects.all()
    
    return render(request, "todo_list.html", 
                {
                    "todo_items": [TodoItemForm(instance=todo_item) for todo_item in all_todo_items],
                    "form": form
                }
            )


def redirect_to_today(request):
    return redirect("/today")

