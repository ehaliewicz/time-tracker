from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View
from django import forms
import dateutil.parser
import logging
from django.db import models,connection
from .models import TodoItem, TodoLog, TodoItemForm, TodoLogForm, ActiveTimer, Stats
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

    update_stats(form.instance.date)
    
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
    

    update_stats(form.instance.date)
    
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

    update_stats(todo_log.date)
    
    return redirect(request.META.get('HTTP_REFERER'))


def delete_todo_item(request, item_id):
    todo_item = TodoItem.objects.get(unique_id=item_id)
    todo_item.delete()

    return redirect(request.META.get('HTTP_REFERER'))


def get_stats_for_filters(tags, **filter_kwargs):
    count = 0
    stats = {}

    agg_params = {
        'time': models.Sum('duration', default=0)
    }
    
    
    stats = TodoLog.objects.filter(**filter_kwargs).aggregate(
        time=models.Sum('duration',default=0),
        count=models.Count('unique_id'),
    )
    
        
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

        
        stats['tags'] = [(tag,cnt,get_hr_min(time)) for (tag,(cnt,time)) in processed_tags_d.items()]
        
    return stats

    

def calculate_stats(date):
    
    start_of_week = date-datetime.timedelta(days=7)
    start_of_month = date-datetime.timedelta(days=30)
    
    todays_stats = get_stats_for_filters(
        tags=False, date=date
    )
    completed_todays_stats = get_stats_for_filters(
        tags=True, date=date, completion=True
    )
    week_stats = get_stats_for_filters(
        tags=True, date__gte=start_of_week, date__lte=date, completion=True
    )
    week_stats['avg'] = week_stats['time']/7
    month_stats = get_stats_for_filters(
        tags=True, date__gte=start_of_month, date__lte=date, completion=True
    )
    month_stats['avg'] = month_stats['time']/30
    
    all_stats = get_stats_for_filters(
        tags=True, completion=True
    )

    pct_tasks = 0
    pct_time = 0

    num_completed_tasks_for_today = completed_todays_stats['count']
    num_tasks_for_today = todays_stats['count']
    completed_time_for_today = completed_todays_stats['time']
    time_for_today = todays_stats['time']
    if num_tasks_for_today != 0:
        pct_tasks = round((num_completed_tasks_for_today*100)/num_tasks_for_today, 2)
        pct_time = round((completed_time_for_today*100)/time_for_today, 2)


    dates = (TodoLog.objects.filter(completion=True)
             .values('date')
             .annotate(count=models.Count('date'))
             .values('date'))

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

    
    first_task = TodoLog.objects.order_by('date').first()
    last_task = TodoLog.objects.order_by('date').last()
    date_interval = last_task.date - first_task.date 
    
    
    return {
        'total_today_tasks': todays_stats['count'],
        'percent_tasks': pct_tasks,
        'percent_time': pct_time,
        'completed_time': get_hr_min(completed_todays_stats['time']),
        'completed_week_time': get_hr_min(week_stats['time']),
        'avg_week_time': get_hr_min(week_stats['avg']),
        'completed_month_time': get_hr_min(month_stats['time']),
        'avg_month_time': get_hr_min(month_stats['avg']),
        
        'total_time': get_hr_min(all_stats['time']),
        'avg_total_time': get_hr_min(all_stats['time']/date_interval.days), 
        'streak': streak,
        'tags': [
            ("This day's tags", list(completed_todays_stats['tags'])), 
            ("Last 7 day's tags", list(week_stats['tags'])), 
            ("Last 30 day's tags", list(month_stats['tags'])), 
            ("All tags", list(all_stats['tags']))],
    }

def update_stats(date):
    c_stats = calculate_stats(date)

    db_stats = Stats.objects.filter(date=date).first()
    if db_stats is None:
        db_stats = Stats(date=date, stats=c_stats)
    else:
        db_stats.stats = c_stats

    db_stats.save()

    # invalid later stats
    later_stats = Stats.objects.filter(date__gt=date)
    for stats in later_stats:
        stats.delete()
        
    return c_stats

def init_stats(date):
    # initializes states on first load, doesn't need to invalidate later stats
    c_stats = calculate_stats(date)

    db_stats = Stats.objects.filter(date=date).first()
    if db_stats is None:
        db_stats = Stats(date=date, stats=c_stats)
    else:
        db_stats.stats = c_stats

    db_stats.save()
    return c_stats


def get_hr_min(m):
    im = int(m)
    return int(im//60), im%60



def inner_date_todo_logs(request, date, title):
    #calced_stats = calculate_stats(date)

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
        timer_lut = {}
        timers = []
    else:
        timers = ActiveTimer.objects.filter(linked_todo_log__in=todo_logs_for_today).distinct()
        timer_lut = {timer.linked_todo_log_id:timer for timer in timers}

    
    queried_stats = Stats.objects.filter(date=date).first()

    if queried_stats is None:
        calced_stats = init_stats(date)
    else:
        calced_stats = queried_stats.stats

    
    new_log = TodoLog(date=date)
    form = TodoLogForm(instance=new_log)

    
    todo_logs_and_timers = [(TodoLogForm(instance=todo_log), timer_lut.get(todo_log.unique_id)) for todo_log in todo_logs_for_today]

    
    
    # TODO: we will only allow one active timer in the future
    if len(timers) == 0:
        active_timer = None
    else:
        active_timer = timers[0]
        
    return render(request, "day_todo_list.html", {
        "title": "Todo List For {}".format(title),
        "todo_logs_and_timers": todo_logs_and_timers,
        "active_timer": active_timer, 
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


def start_timer(request, log_id):
    ActiveTimer(linked_todo_log_id=log_id).save()
    return redirect("/today/")


def pause_timer(request, log_id):
    t = ActiveTimer.objects.filter(linked_todo_log_id=log_id).get()
    t.paused = datetime.datetime.now()
    t.save()
    return redirect("/today/")


def resume_timer(request, log_id):
    t = ActiveTimer.objects.filter(linked_todo_log_id=log_id).get()

    paused_d = t.paused
    now_d = datetime.datetime.now(datetime.timezone.utc)
    
    
    paused_dt = now_d - paused_d # amount of time paused

    t.paused = None
    t.started += paused_dt # move start time forward by how long it was paused

    t.save()
    return redirect("/today/")


def stop_timer(request, log_id):
    t = ActiveTimer.objects.filter(linked_todo_log_id=log_id).get()

    start_d = t.started

    if t.paused is not None:
        end_d = t.paused
    else:
        end_d = datetime.datetime.now(datetime.timezone.utc) 

    duration = round((end_d - start_d).total_seconds()/60)

    log = TodoLog.objects.filter(unique_id=log_id).get()

    log.duration = duration
    log.completion = True
    t.delete()
    log.save()


    update_stats(t.datetime.date())
        
    return redirect("/today/")
    
