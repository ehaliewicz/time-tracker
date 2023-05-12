from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_protect, csrf_exempt, ensure_csrf_cookie
import datetime
import dateutil.parser
import json
import logging
import pytz
import time

import todo.todo_logs as todo_logs
from .models import TodoItem, TodoLog, ActiveTimer, ActiveTimerSerializer, TodoLogSerializer
from .stats import get_or_cache_stats, update_stats
from .forms import TodoLogForm
from datetime import datetime


def api_login_required(endpoint):
    def inner(request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            return endpoint(request, *args, **kwargs)
        return HttpResponse(status=401)
    return inner

def serialized_endpoint(serializer_cls):
    def decorator(endpoint):
        def inner(req, *args, **kwargs):
            try:
                resp = endpoint(req, *args, **kwargs)
                dat = serializer_cls(resp).data
                return JsonResponse(dat, safe=False)
            except:
                raise
        return inner
    return decorator



@login_required
@ensure_csrf_cookie
@csrf_protect
@serialized_endpoint(TodoLogSerializer)
def get_todo_log(request, log_id):
    log = TodoLog.objects.get(user_id=request.user.id, unique_id=log_id)
    return log



@login_required
@ensure_csrf_cookie
@csrf_protect
@serialized_endpoint(TodoLogSerializer)
def update_todo_log(request, log_id):
    start = datetime.now()
    data = json.loads(request.body)
    after_parse = datetime.now()
    form = TodoLogForm(data)
    after_form_create = datetime.now()
    if form.is_valid():
        after_form_check = datetime.now()
        form.instance.unique_id = log_id
        form.instance.user_id = request.user.id
        form.instance.save()
        after_form_save = datetime.now()
    else:
        raise Exception("Error(s) updating todo log {}".format(form.errors))
    
    update_stats(request.user.id, form.instance.date)
    after_update_stats = datetime.now()
    logging.info("""
    parse input {}ms
    create form {}ms
    form check {}ms
    form save {}ms
    update stats{}ms
    """.format((after_parse-start).total_seconds()*1000,
               (after_form_create - after_parse).total_seconds()*1000,
               (after_form_check - after_form_create).total_seconds()*1000,
               (after_form_save - after_form_check).total_seconds()*1000,
               (after_update_stats - after_form_save).total_seconds()*1000,
               ))
    return form.instance


@login_required
@ensure_csrf_cookie
@csrf_protect
def delete_todo_log(request, log_id):
    todo_log = TodoLog.objects.get(user_id=request.user.id,unique_id=log_id)
    todo_log.delete()

    update_stats(request.user.id, todo_log.date)
    
    return HttpResponse(status=200)


@csrf_protect
@ensure_csrf_cookie
@login_required
@serialized_endpoint(TodoLogSerializer)
def new_todo_log(request):
    data = json.loads(request.body)
    form = TodoLogForm(data)
    if form.is_valid():
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) creating todo log {}".format(form.errors))
    

    update_stats(request.user.id, form.instance.date)

    return form.instance


class ListSerializer(object):
    def __init__(self, item_serializer):
        self.item_serializer = item_serializer
        
    
    def bind_lst(self, lst):
        self.data = [self.item_serializer(i).data for i in lst]
        return self



def todoItemToLog(user_id,item, date):
    return TodoLog(
        user_id=user_id,
        description=item.description,
        duration=item.duration,
        tag=item.tag,
        date=date
    )
    
@login_required
@ensure_csrf_cookie
@csrf_protect
@serialized_endpoint(ListSerializer(TodoLogSerializer).bind_lst)
def todo_logs_for_day(request, date):
    parsed_date = dateutil.parser.parse(date)
    todo_logs_for_day = todo_logs.get_logs_for_date(request.user.id, date, sort_by='unique_id')

    
    if len(todo_logs_for_day) == 0:
        # create a list of TodoLogs from TodoItems
        all_todo_items = TodoItem.objects.filter(user_id=request.user.id)
        
        new_todo_logs = [todoItemToLog(request.user.id, item, date) for item in all_todo_items]
        TodoLog.objects.bulk_create(new_todo_logs)
        todo_logs_for_day = todo_logs.get_logs_for_date(request.user.id, date, sort_by='unique_id')
        
        
    #timer = ActiveTimer.objects.filter(user_id=request.user.id).first()
    return list(todo_logs_for_day)
    #return JsonResponse([TodoLogSerializer(m).data for m in todo_logs_for_today], safe=False)


@login_required
@ensure_csrf_cookie
@csrf_protect
def stats_for_day(request, date):
    parsed_date = dateutil.parser.parse(date)
    calced_stats = get_or_cache_stats(request.user.id, parsed_date)
    return JsonResponse(calced_stats)



@csrf_protect
@ensure_csrf_cookie
@login_required
def get_timer(request, date):
    parsed_date = dateutil.parser.parse(date)
    timers = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log__date=parsed_date)
    if len(timers) == 0:
        return JsonResponse({})
    else:
        assert len(timers) == 1
        timer = timers[0]
        return JsonResponse(ActiveTimerSerializer(timer).data)


@csrf_protect
@ensure_csrf_cookie
@login_required
@serialized_endpoint(ActiveTimerSerializer)
def start_timer(request, log_id):
    timer = ActiveTimer(user_id=request.user.id, linked_todo_log_id=log_id)
    timer.save()
    return timer


@csrf_protect
@ensure_csrf_cookie
@login_required
@serialized_endpoint(ActiveTimerSerializer)
def pause_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()
    t.paused = datetime.datetime.now(datetime.timezone.utc)
    t.save()
    return t


@csrf_protect
@ensure_csrf_cookie
@login_required
@serialized_endpoint(ActiveTimerSerializer)
def resume_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()
    paused_d = pytz.utc.localize(t.paused)
    now_d = datetime.datetime.now(datetime.timezone.utc)
    
    
    paused_dt = now_d - paused_d # amount of time paused

    t.paused = None
    t.started += paused_dt # move start time forward by how long it was paused

    t.save()
    return t

    
@csrf_protect
@ensure_csrf_cookie
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

    update_stats(request.user.id, log.date)
    return HttpResponse(status=200)


@csrf_protect
@ensure_csrf_cookie
@login_required
def delete_timer(request, log_id):
    t = ActiveTimer.objects.filter(user_id=request.user.id, linked_todo_log_id=log_id).get()
    t.delete()

    return HttpResponse(status=200)
