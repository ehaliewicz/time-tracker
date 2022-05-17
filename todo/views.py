from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View
from django import forms
import dateutil.parser
import logging

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

def get_tag_info(todo_logs):
    for log in todo_logs:
        if log.tag is None or log.tag == "":
            log.tag = "untagged"
    time_lookup = collections.defaultdict(int)
    tag_counts = collections.Counter([log.tag for log in todo_logs])
    for log in todo_logs:
        time_lookup[log.tag] += log.duration
    for (tag,cnt) in tag_counts.items():
        yield (tag,cnt,get_hr_min(time_lookup[tag]))

def calculate_stats(date):
    
    start_of_week = date-datetime.timedelta(days=7)

    all_todo_logs_for_today = TodoLog.objects.filter(date=date)
    completed_todo_logs_for_today = [t for t in all_todo_logs_for_today if t.completion]
    pct_tasks = round(100*len(completed_todo_logs_for_today)/len(all_todo_logs_for_today), 2)
    pct_time = round(100*sum([t.duration for t in completed_todo_logs_for_today])/sum([t.duration for t in all_todo_logs_for_today]), 2)
    
    
    completed_time = sum([log.duration for log in completed_todo_logs_for_today])

    todo_logs_for_week = TodoLog.objects.filter(date__gte=start_of_week, date__lte=date, completion=True)
    completed_week = sum([log.duration for log in todo_logs_for_week])

    all_todo_logs = list(TodoLog.objects.filter(completion=True))
    completed_total = sum([log.duration for log in all_todo_logs])

    completed_dates = set([(log.date.year, log.date.month, log.date.day) for log in all_todo_logs])

    todays_tags = get_tag_info(completed_todo_logs_for_today)
    week_tags = get_tag_info(todo_logs_for_week)
    all_tags = get_tag_info(all_todo_logs)


    def has_date(d):
        return (d.year,d.month,d.day) in completed_dates
    
    cur_date = date
    streak = 0
    while True:
        if not has_date(cur_date):
            break
        streak += 1
        cur_date = cur_date - datetime.timedelta(days=1)

    ##todays_tag_items = ((tag,cnt, get_hr_min(todays_tag_time_lookup[tag])) for tag,cnt in todays_tags.items())


    return {
        'percent_tasks': pct_tasks,
        'percent_time': pct_time,
        'completed_time': get_hr_min(completed_time),
        'completed_week_time': get_hr_min(completed_week),
        'total_time': get_hr_min(completed_total),
        'streak': streak,
        'tags': [("This day's tags", list(todays_tags)), ('Week tags', list(week_tags)), ('All tags', list(all_tags))],

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

    calced_stats = calculate_stats(date)

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
