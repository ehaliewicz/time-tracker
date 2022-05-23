from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View
from django import forms
import collections
import datetime
import dateutil.parser
from django.contrib.auth.decorators import login_required
from django.db import models,connection
import logging

from .models import TodoItem, TodoLog, ActiveTimer
from .forms import TodoItemForm, TodoLogForm, RegisterForm



from .stats import get_or_cache_stats, update_stats
import pytz
from django.views.decorators import cache


def todoItemToLog(user_id,item, date):
    return TodoLog(
        user_id=user_id,
        description=item.description,
        duration=item.duration,
        tag=item.tag,
        date=date
    )


class ImportLogsForm(forms.Form):
    log_file = forms.FileField()
    


### parsing and unparsing
def skip_char(c, line):
    if len(line) == 0:
        raise Exception("Expected '{}' but got EOL".format(c))
    if line[0] != c:
        raise Exception("Expected '{}' but got '{}'".format(c, line[0]))

    return line[1:]


def skip_string(s, line):
    while len(s) > 0:
        line = skip_char(s[0], line)
        s = s[1:]
    return line
        
def skip_whitespace(line):
    idx = 0
    rem = len(line)
    while rem > 0 and line[idx].isspace():
        #line = line[1:]
        idx += 1
        rem -= 1
        
    return line[idx:]

def parse_time(time_str):
    assert time_str[-1] == 'm', "Expected time with 'm' suffix"
    return int(time_str[:-1])


def parse_todo_line(line, date):
    line = skip_char('#', line)
    line = skip_whitespace(line)

    done = False
    try: 
        line = skip_string('DONE', line)
        done = True
    except:
        pass

    line = skip_whitespace(line)

    spl = line.split(" (", 1)
    todo_name, line = spl[0],spl[1]
    
    todo_description = todo_name.rstrip()
    
    spl = line.split(")", 1)
    time,line = spl[0],spl[1]

    time_duration = parse_time(time)
        
    line = skip_whitespace(line)

    tag = ""
    if len(line) > 0:
        # parse a tag
        line = skip_char('%', line)
        tag = line.strip()
    
    return TodoLog(user_id=request.user.id, description=todo_description, duration=time_duration, completion=done, tag=tag, date=date)



def handle_log_form(form):
    log_file = form.cleaned_data['log_file']
    date_str = log_file.name.split("_log.txt")[0]
    date = dateutil.parser.parse(date_str)

    logs = []
    for line in log_file:
        todo_log = parse_todo_line(line.decode('utf-8'), date)
        logs.append(todo_log)
        
    for log in logs:
        log.save()
    
    return date_str

@login_required
def import_logs_for_date(request):
    if request.method == 'POST':
        form = ImportLogsForm(request.POST, request.FILES)
        if form.is_valid():
            date = handle_log_form(form)
            return redirect('/day/{}'.format(date))
        else:
            raise Exception("Error importing log file {}".format(form.errors))
    else:
        form = ImportLogsForm()
        return render(request, "import_logs.html", {
            "form": form,
        })
            
    pass


def todo_list_or_defaults(user_id):
    all_todo_items = TodoItem.objects.filter(user_id=user_id)
    return all_todo_items

@login_required
def update_todo_log(request, log_id):
    form = TodoLogForm(request.POST)
    if form.is_valid():
        form.instance.unique_id = log_id
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) updating todo log {}".format(form.errors))

    update_stats(request.user.id, form.instance.date)
    
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def update_todo_item(request, item_id):
    form = TodoItemForm(request.POST)
    if form.is_valid():
        form.instance.user_id = request.user.id
        form.instance.unique_id = item_id
        form.instance.save()
    else:
        raise Exception("Error(s) updating todo item {}".format(form.errors))
    
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def new_todo_log(request):
    form = TodoLogForm(request.POST)
    if form.is_valid():
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo log {}".format(form.errors))
    

    update_stats(request.user.id, form.instance.date)
    
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def new_todo_item(request):
    form = TodoItemForm(request.POST)
    if form.is_valid():
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo item {}".format(form.errors))
    
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def delete_todo_log(request, log_id):
    todo_log = TodoLog.objects.get(user_id=request.user.id,unique_id=log_id)
    todo_log.delete()

    update_stats(request.user.id, todo_log.date)
    
    return redirect(request.META.get('HTTP_REFERER'))

@login_required
def delete_todo_item(request, item_id):
    todo_item = TodoItem.objects.get(user_id=request.user.id, unique_id=item_id)
    todo_item.delete()

    return redirect(request.META.get('HTTP_REFERER'))



def inner_date_todo_logs(request, date, title, templ):
    
    todo_logs_for_today = TodoLog.objects.filter(user_id=request.user.id,date=date).order_by('unique_id')
    if len(todo_logs_for_today) == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = todo_list_or_defaults(request.user.id)

        new_todo_logs = []
        for item in all_todo_items:
            log = todoItemToLog(request.user.id, item, date)
            log.save()
            new_todo_logs.append(log)

        todo_logs_for_today = new_todo_logs
        timer_lut = {}
        timers = []
    else:
        timers = ActiveTimer.objects.filter(linked_todo_log__in=todo_logs_for_today).distinct()
        timer_lut = {timer.linked_todo_log_id:timer for timer in timers}

    calced_stats = get_or_cache_stats(request.user.id, date)
    
    new_log = TodoLog(user_id=request.user.id, date=date)
    form = TodoLogForm(instance=new_log)

    
    todo_logs_and_timers = [(TodoLogForm(instance=todo_log), timer_lut.get(todo_log.unique_id)) for todo_log in todo_logs_for_today]

    
    
    # TODO: we will only allow one active timer in the future
    if len(timers) == 0:
        active_timer = None
    else:
        active_timer = timers[0]
        
    return render(request, templ, { #"day_todo_list.html", {
        "title": "Todo List For {}".format(title),
        "todo_logs_and_timers": todo_logs_and_timers,
        "active_timer": active_timer, 
        "form": form,
        **calced_stats
    })


@login_required
@csrf_protect
def todays_todos(request):
    tz_name = request.session['tz_name']
    date = datetime.datetime.now(pytz.timezone(tz_name))
    title = "{}/{}/{}".format(date.year, date.month, date.day) 
    
    return inner_date_todo_logs(request, date, title, "day_todo_list.html")

@login_required
@csrf_protect
def todays_todos_jinja(request):
    tz_name = request.session['tz_name']
    date = datetime.datetime.now(pytz.timezone(tz_name))
    title = "{}/{}/{}".format(date.year, date.month, date.day) 
    
    return inner_date_todo_logs(request, date, title, "day_todo_list.jinja")


@login_required
@csrf_protect
def date_todos(request, date):
    date = dateutil.parser.parse(date)
    title = "{}/{}/{}".format(date.year, date.month, date.day)
    return inner_date_todo_logs(request, date, title, "day_todo_list.html")


@login_required
@csrf_protect
def todo_list(request):
    form = TodoItemForm()
    all_todo_items = TodoItem.objects.filter(user_id=request.user.id)
    
    return render(request, "todo_list.html", 
                {
                    "todo_items": [TodoItemForm(instance=todo_item) for todo_item in all_todo_items],
                    "form": form
                }
            )


@login_required
def redirect_to_today(request):
    return redirect("/today")
    

@login_required
def list_todo_logs_for_tag(request, tag):
    q = TodoLog.objects.filter(user_id=request.user.id,tag=tag)
    return render(request, "todo_logs_by_tag.html",
            {
                "tag": tag,
                "todo_logs": [TodoLogForm(instance=log) for log in q]
            })

@login_required
def start_timer(request, log_id):
    ActiveTimer(user_id=request.user.id, linked_todo_log_id=log_id).save()
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def pause_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()
    t.paused = datetime.datetime.now(datetime.timezone.utc)
    t.save()
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def resume_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()
    paused_d = pytz.utc.localize(t.paused)
    now_d = datetime.datetime.now(datetime.timezone.utc)
    
    
    paused_dt = now_d - paused_d # amount of time paused

    t.paused = None
    t.started += paused_dt # move start time forward by how long it was paused

    t.save()
    return redirect(request.META.get('HTTP_REFERER'))
    

@login_required
def stop_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()

    start_d = pytz.utc.localize(t.started)

    if t.paused is not None:
        end_d = pytz.utc.localize(t.paused)
    else:
        end_d = datetime.datetime.now(datetime.timezone.utc) 

    duration = round((end_d - start_d).total_seconds()/60)

    log = TodoLog.objects.filter(user_id=request.user.id, unique_id=log_id).get()

    log.duration = duration
    log.completion = True
    t.delete()
    log.save()

    update_stats(request.user.id, t.started.date())
    return redirect(request.META.get('HTTP_REFERER'))
    

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            raise Exception("Invalid registration: {}".format(form.errors))
        return redirect("/today")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


"""
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
        else:
            return 
"""
