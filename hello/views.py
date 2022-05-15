from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views import View

from .models import TodoItem, TodoLog, TodoItemForm, TodoLogForm
import datetime

def todoItemToLog(item, date):
    return TodoLog(
        description=item.description,
        duration=item.duration,
        tag=item.tag,
        date=date
    )

DEFAULT_TODOS = [
    TodoItem(description= '1x podcast #1', duration=15, tag='podcast'),
    TodoItem(description='1x podcast #1', duration=15, tag='podcast '),
    TodoItem(description='1x podcast #1', duration=15, tag='podcast'),
    TodoItem(description='1x podcast #2', duration=15, tag='podcast'),
    TodoItem(description='1x podcast #2', duration=15, tag='podcast'),
    TodoItem(description='1x podcast #2', duration=15, tag='podcast'),
    TodoItem(description='transcribe short podcast', duration=20, tag='transcribed-podcast'),
    TodoItem(description='30m passive audio', duration=30, tag=''),
    TodoItem(description='30m passive audio', duration=30, tag=''),
    TodoItem(description='30m passive audio', duration=30, tag=''),
    TodoItem(description='1 episode of show', duration=20, tag='episode'),
    TodoItem(description='1 episode of anime', duration=20, tag='episode'),
    TodoItem(description='1 nhk news easy', duration=3, tag='nhk-easy-article'),
    TodoItem(description='1 nhk news easy', duration=3, tag='nhk-easy-article'),
    TodoItem(description='1 nhk news easy', duration=3, tag='nhk-easy-article'),
    TodoItem(description='1 page of read real japanese', duration=15, tag='essay-page'),
    TodoItem(description='1 chapter of manga', duration=12, tag='manga-chapter'),
    TodoItem(description='1 chapter of manga', duration=12, tag='manga-chapter'),
    
]

def todo_list_or_defaults():
    all_todo_items = TodoItem.objects.all()
    if len(all_todo_items) == 0:
        return DEFAULT_TODOS
    else:
        return all_todo_items


class UpdateLogView(View):
    http_method_names = ['post']

    def post(self, request, log_id):
        form = TodoLogForm(request.POST)
        if form.is_valid():
            form.instance.unique_id = log_id
            form.instance.save()
        else:
            raise Exception("Error(s) updating or creating todo log {}".format(form.errors))
    
    
        return redirect("/today")


def calculate_stats():
    
    today = datetime.date.today()
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

@csrf_protect
def todays_todos(request):
    today = datetime.date.today()

    todo_logs_for_today = TodoLog.objects.filter(date=today).order_by('unique_id')


    if len(todo_logs_for_today) == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = todo_list_or_defaults() #TodoItem.objects.all()

        new_todo_logs = []
        for item in all_todo_items:
            log = todoItemToLog(item, today)
            log.save()
            new_todo_logs.append(log)

        todo_logs_for_today = new_todo_logs

    calced_stats = calculate_stats()
    
    return render(request, "todays_todos.html", {
        "todo_logs": [TodoLogForm(instance=todo_log) for todo_log in todo_logs_for_today],
        **calced_stats
    })


@csrf_protect
def todo_list(request):
    if request.method == 'POST':
        form = TodoItemForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            raise Exception("Error creating new todo item")
    else:
        form = TodoItemForm()

    #greeting = Greeting()
    #greeting.save()

    #greetings = Greeting.objects.all()

    all_todo_items = todo_list_or_defaults #TodoItem.objects.all()
    return render(request, "todo_list.html", 
                {
                    "todo_items": all_todo_items,
                    "form": form
                }
            )


def redirect_to_today(request):
    return redirect("/today")

