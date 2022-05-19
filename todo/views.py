from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View
from django import forms
import dateutil.parser
import logging
from django.db import models,connection
from .models import TodoItem, TodoLog, TodoItemForm, TodoLogForm
import datetime
import collections

def todoItemToLog(item, date):
    return TodoLog(
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
    
    return TodoLog(description=todo_description, duration=time_duration, completion=done, tag=tag, date=date)



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


def import_todo_file(request):
    pass
    

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


def get_stats_for_filters(tags, get_num_tasks, **filter_kwargs):
    count = 0
    if get_num_tasks:
        time_count_stats = TodoLog.objects.filter(**filter_kwargs).aggregate(
            time=models.Sum('duration',default=0),
            count=models.Count('unique_id')
        )
    
        time = time_count_stats['time']
        count = time_count_stats['count']
    else:
        time_count_stats = TodoLog.objects.filter(**filter_kwargs).aggregate(
            time=models.Sum('duration',default=0),
        )
    
        time = time_count_stats['time']

    processed_tags = []
    if tags:
        tags = (TodoLog.objects
                .filter(**filter_kwargs)
                .values('tag')
                .annotate(count=models.Count('tag'),time=models.Sum('duration')))
    
        processed_tags_d = {}
        for t in tags:
            tag = t['tag']
            if tag is None or tag == '':
                tag = 'Untagged'
            if tag not in processed_tags_d:
                processed_tags_d[tag] = (0,0)
            cnt,tme = processed_tags_d[tag]
            cnt += t['count']
            tme += t['time']
            processed_tags_d[tag] = cnt,tme

        
        processed_tags = [(tag,cnt,get_hr_min(time)) for (tag,(cnt,time)) in processed_tags_d.items()]

    return time,count,processed_tags

def calculate_stats(date):
    
    start_of_week = date-datetime.timedelta(days=7)
    
    time_for_today, num_tasks_for_today, _ = get_stats_for_filters(
        tags=False, get_num_tasks=True, date=date
    )
    completed_time_for_today, num_completed_tasks_for_today, todays_tags = get_stats_for_filters(
        tags=True, get_num_tasks=True, date=date, completion=True
    )
    completed_time_for_week, _, week_tags = get_stats_for_filters(
        tags=True, get_num_tasks=False, date__gte=start_of_week, date__lte=date, completion=True
    )
    completed_time_for_month, _, month_tags = get_stats_for_filters(
        tags=True, get_num_tasks=False, date__gte=start_of_week, date__lte=date, completion=True
    )
    completed_all_time, _, all_tags = get_stats_for_filters(
        tags=True, get_num_tasks=False, completion=True
    )

    pct_tasks = 0
    pct_time = 0
    if num_tasks_for_today != 0:
        pct_tasks = round((num_completed_tasks_for_today*100)/num_tasks_for_today, 2)
        pct_time = round((completed_time_for_today*100)/time_for_today, 2)


    dates = TodoLog.objects.filter(completion=True).values('date').annotate(count=models.Count('date'))
    completed_dates = set((d.year, d.month, d.day) for d in (r['date'] for r in dates))


    def has_date(d):
        return (d.year,d.month,d.day) in completed_dates
    
    cur_date = date
    streak = 0
    while True:
        if not has_date(cur_date):
            break
        streak += 1
        cur_date = cur_date - datetime.timedelta(days=1)


    return {
        'percent_tasks': pct_tasks,
        'percent_time': pct_time,
        'completed_time': get_hr_min(completed_time_for_today),
        'completed_week_time': get_hr_min(completed_time_for_week),
        'completed_month_time': get_hr_min(completed_time_for_week),
        'total_tasks': num_tasks_for_today,
        'total_time': get_hr_min(completed_all_time),
        'streak': streak,
        'tags': [
            ("This day's tags", list(todays_tags)), 
            ('Last 7 day\s tags', list(week_tags)), 
            ('Last 30 day\s tags', list(month_tags)), 
            ('All tags', list(all_tags))],
    }


def get_hr_min(m):
    return int(m//60), m%60



def inner_date_todo_logs(request, date, title):
    calced_stats = calculate_stats(date)
    
    if calced_stats['total_tasks'] == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = todo_list_or_defaults() #TodoItem.objects.all()

        new_todo_logs = []
        for item in all_todo_items:
            log = todoItemToLog(item, date)
            log.save()
            new_todo_logs.append(log)

        todo_logs_for_today = new_todo_logs
        calced_stats = calculate_stats(date)
    else:
        todo_logs_for_today = TodoLog.objects.filter(date=date).order_by('unique_id')

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


def list_todo_logs_for_tag(request, tag):
    q = TodoLog.objects.filter(tag=tag)
    return render(request, "todo_logs_by_tag.html",
            {
                "tag": tag,
                "todo_logs": [TodoLogForm(instance=log) for log in q]
            })
