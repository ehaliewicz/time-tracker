from django.shortcuts import redirect, render
from django.http import HttpResponse

from .models import TodoItem, TodoLog
import datetime

# Create your views here.
def index(request):
    # return HttpResponse('Hello from Python!')
    return render(request, "index.html")


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
    

def todays_todos(request):

    #greeting = Greeting()
    #greeting.save()

    #greetings = Greeting.objects.all()

    today = datetime.date.today()

    todo_logs_for_today = TodoLog.objects.filter(date=today)
    if len(todo_logs_for_today) == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = todo_list_or_defaults() #TodoItem.objects.all()

        new_todo_logs = []
        for item in all_todo_items:
            log = todoItemToLog(item,today)
            log.save()
            new_todo_logs.append(log)

        todo_logs_for_today = new_todo_logs

    
    return render(request, "todays_todos.html", {"todo_logs": todo_logs_for_today}) #greetings})


def todo_list(request):

    #greeting = Greeting()
    #greeting.save()

    #greetings = Greeting.objects.all()

    all_todo_items = todo_list_or_defaults #TodoItem.objects.all()
    return render(request, "todo_list.html", {"todo_items": all_todo_items})


def redirect_to_today(request):
    return redirect("/today")