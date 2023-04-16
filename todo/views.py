from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt, ensure_csrf_cookie
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
import todo.todo_logs as todo_logs


from .stats import get_or_cache_stats, update_stats, calculate_cumulative_stats
import pytz
from django.views.decorators import cache


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

        tz_name = request.session['tz_name']
        date = datetime.datetime.now(pytz.timezone(tz_name))
        fmt_date = "{}-{}-{}".format(date.year, date.month, date.day) 
        form = ImportLogsForm()
        return render(request, "import_logs.html", {
            "form": form,
            "date": fmt_date,
        })
            
    pass


def todo_list_or_defaults(user_id):
    all_todo_items = TodoItem.objects.filter(user_id=user_id)
    return all_todo_items


@csrf_protect
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

@csrf_protect
@login_required
def new_todo_item(request):
    form = TodoItemForm(request.POST)
    if form.is_valid():
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo item {}".format(form.errors))
    
    return redirect(request.META.get('HTTP_REFERER'))


@csrf_protect
@login_required
def delete_todo_item(request, item_id):
    todo_item = TodoItem.objects.get(user_id=request.user.id, unique_id=item_id)
    todo_item.delete()

    return redirect(request.META.get('HTTP_REFERER'))



def inner_date_todo_logs(request, date, fmt_date, templ):
    
    todo_logs_for_today = todo_logs.get_logs_for_date(request.user.id, date, sort_by='unique_id')
    
    return render(request, templ, { #"day_todo_list.html", {
        "title": "Todo List For {}".format(fmt_date),
        "date": fmt_date,
    })


@login_required
@csrf_protect
def todays_todos(request):
    tz_name = request.session['tz_name']
    date = datetime.datetime.now(pytz.timezone(tz_name))
    fmt_date = "{}-{}-{}".format(date.year, date.month, date.day) 
    
    return inner_date_todo_logs(request, date, fmt_date, "day_todo_list.html")


@login_required
@csrf_protect
def date_todos(request, date):
    date = dateutil.parser.parse(date)
    fmt_date = "{}-{}-{}".format(date.year, date.month, date.day)
    return inner_date_todo_logs(request, date, fmt_date, "day_todo_list.html")


@login_required
@csrf_protect
def todo_list(request):
    form = TodoItemForm()
    all_todo_items = TodoItem.objects.filter(user_id=request.user.id)

    tz_name = request.session['tz_name']
    date = datetime.datetime.now(pytz.timezone(tz_name))
    fmt_date = "{}-{}-{}".format(date.year, date.month, date.day) 
    
    return render(request, "todo_list.html", 
                {
                    "todo_items": [TodoItemForm(instance=todo_item) for todo_item in all_todo_items],
                    "form": form,
                    "date": fmt_date,
                }
            )


@login_required
def redirect_to_today(request):
    return redirect("/today")
    

@login_required
def list_todo_logs_for_tag(request, tag):
    q = TodoLog.objects.filter(user_id=request.user.id,tag=tag)

    tz_name = request.session['tz_name']
    date = datetime.datetime.now(pytz.timezone(tz_name))
    fmt_date = "{}-{}-{}".format(date.year, date.month, date.day) 
    return render(request, "todo_logs_by_tag.html",
            {
                "tag": tag,
                "todo_logs": [TodoLogForm(instance=log) for log in q],
                "date": fmt_date,
            })



@csrf_protect
def full_stats(request):
    tag = request.GET.get('tag', None)
    (per_month_chart, per_month_count_chart,
    cumulative_chart, cumulative_count_chart, all_tags) = calculate_cumulative_stats(request.user.id, tag=tag)
    return render(request, "full_stats.html",
                  {
                      "per_month_chart": per_month_chart,
                      "cumulative_chart": cumulative_chart,
                      "per_month_count_chart": per_month_count_chart,
                      "cumulative_count_chart": cumulative_count_chart,
                      "all_tags": all_tags,
                      "cur_tag": tag
                  })
    

@csrf_protect
@login_required
def stop_timer(request, log_id):
    stop_timer_inner(request, log_id)
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
