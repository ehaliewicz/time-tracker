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
from .models import TodoLog, ActiveTimer, ActiveTimerSerializer, TodoLogSerializer
from .stats import get_or_cache_stats, update_stats
from .forms import TodoLogForm


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
    data = json.loads(request.body)
    form = TodoLogForm(data)
    if form.is_valid():
        form.instance.unique_id = log_id
        form.instance.user_id = request.user.id
        form.instance.save()
    else:
        raise Exception("Error(s) updating todo log {}".format(form.errors))

    update_stats(request.user.id, form.instance.date)
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

@login_required
@ensure_csrf_cookie
@csrf_protect
@serialized_endpoint(ListSerializer(TodoLogSerializer).bind_lst)
def todo_logs_for_day(request, date):
    parsed_date = dateutil.parser.parse(date)
    todo_logs_for_today = todo_logs.get_logs_for_date(request.user.id, date, sort_by='unique_id')
    
    #timer = ActiveTimer.objects.filter(user_id=request.user.id).first()
    return list(todo_logs_for_today)
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
def get_timer(request):
    timers = ActiveTimer.objects.filter(user_id=request.user.id)
    if len(timers) == 0:
        return JsonResponse({})
    else:
        return JsonResponse(ActiveTimerSerializer(timers[0]).data)


@csrf_protect
@ensure_csrf_cookie
@login_required
@serialized_endpoint(ActiveTimerSerializer)
def start_timer(request, log_id):
    time.sleep(10)
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
    #time.sleep(10)
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
