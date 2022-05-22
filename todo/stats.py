from .models import Stats, TodoLog
import datetime
from django.db import models
import logging

def get_hr_min(m):
    im = int(m)
    return int(im//60), im%60


def get_stats_for_filters(user_id, tags, **filter_kwargs):
    count = 0
    stats = {}

    agg_params = {
        'time': models.Sum('duration', default=0)
    }
    
    
    stats = TodoLog.objects.filter(
        user_id=user_id,
        **filter_kwargs
    ).aggregate(
        time=models.Sum('duration',default=0),
        count=models.Count('unique_id'),
    )
    
        
    processed_tags = []
    if tags:
        tags = (TodoLog.objects.filter(
            user_id=user_id,
            **filter_kwargs
        ).values(
            'tag'
        ).annotate(count=models.Count('tag'),time=models.Sum('duration')))
    
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


def calculate_stats(user_id, date):
    
    start_of_week = date-datetime.timedelta(days=7)
    start_of_month = date-datetime.timedelta(days=30)
    
    todays_stats = get_stats_for_filters(
        user_id=user_id, tags=False, date=date
    )
    completed_todays_stats = get_stats_for_filters(
        user_id=user_id,tags=True, date=date, completion=True
    )
    week_stats = get_stats_for_filters(
        user_id=user_id,tags=True, date__gte=start_of_week, date__lte=date, completion=True
    )
    week_stats['avg'] = week_stats['time']/7
    month_stats = get_stats_for_filters(
        user_id=user_id,tags=True, date__gte=start_of_month, date__lte=date, completion=True
    )
    month_stats['avg'] = month_stats['time']/30
    
    all_stats = get_stats_for_filters(
        user_id=user_id,tags=True, completion=True
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


    dates = (TodoLog.objects
             .filter(user_id=user_id, completion=True)
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

    
    first_task = TodoLog.objects.filter(user_id=user_id).order_by('date').first()
    last_task = TodoLog.objects.filter(user_id=user_id).order_by('date').last()
    if first_task and last_task and first_task.date != last_task.date:
        date_interval = last_task.date - first_task.date
        avg_total_time = get_hr_min(all_stats['time']/date_interval.days)
        num_total_days = date_interval.days
    else:
        avg_total_time = all_stats['time']
        num_total_days = 1 if first_task or last_task else 0
        
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
        'avg_total_time': avg_total_time,
        'num_total_days': num_total_days, 
        'streak': streak,
        'tags': [
            ("This day's tags", list(completed_todays_stats['tags'])), 
            ("Last 7 day's tags", list(week_stats['tags'])), 
            ("Last 30 day's tags", list(month_stats['tags'])), 
            ("All tags", list(all_stats['tags']))],
    }



def init_stats(user_id,date):
    # initializes states on first load, doesn't need to invalidate later stats
    c_stats = calculate_stats(user_id,date)

    db_stats = Stats.objects.filter(user_id=user_id,date=date).first()
    if db_stats is None:
        db_stats = Stats(user_id=user_id,date=date, stats=c_stats)
    else:
        db_stats.stats = c_stats

    db_stats.save()
    return c_stats

def update_stats(user_id,date):
    c_stats = calculate_stats(user_id,date)

    db_stats = Stats.objects.filter(user_id=user_id,date=date).first()
    if db_stats is None:
        db_stats = Stats(user_id=user_id,date=date, stats=c_stats)
    else:
        db_stats.stats = c_stats

    db_stats.save()

    # invalid later stats
    later_stats = Stats.objects.filter(user_id=user_id,date__gt=date)
    for stats in later_stats:
        stats.delete()
        
    return c_stats


def get_or_cache_stats(user_id,date):
    
    
    queried_stats = Stats.objects.filter(user_id=user_id,date=date).first()
    
    if queried_stats is None:
        calced_stats = init_stats(user_id,date)
    else:
        calced_stats = queried_stats.stats


    return calced_stats
