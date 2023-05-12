from .models import Stats, TodoLog
import datetime
from django.db import models
from django.contrib.postgres import aggregates
import itertools
import logging


import plotly.graph_objects as go
import urllib.parse


def get_hr_min(m):
    im = int(m)
    return int(im//60), im%60


def get_stats_for_filters(user_id, tags, logs_plot_data, **filter_kwargs):
    count = 0
    stats = {}

    
    agg_params = {
        'time': models.Sum('duration', default=0),
        'count': models.Count('unique_id')
    }

    
    
    if logs_plot_data:
        agg_params['log_durations'] = aggregates.ArrayAgg('duration')
        agg_params['log_tags'] = aggregates.ArrayAgg('tag')
        agg_params['log_dates'] = aggregates.ArrayAgg('date')

    stats = TodoLog.objects.filter(
        user_id=user_id,
        **filter_kwargs
    ).aggregate(
        **agg_params        
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
    
    start_of_week = date-datetime.timedelta(days=6)
    start_of_month = date-datetime.timedelta(days=30)
    
    todays_stats = get_stats_for_filters(
        user_id=user_id, tags=False, logs_plot_data=False, date=date
    )
    #print("todays stats: ", todays_stats)

    ### QUERY
    completed_todays_stats = get_stats_for_filters(
        user_id=user_id,tags=True, logs_plot_data=False, date=date, completion=True
    )
    #print("completed todays stats: ", completed_todays_stats)

    ### QUERY
    week_stats = get_stats_for_filters(
        user_id=user_id,tags=True, logs_plot_data=True, date__gte=start_of_week, date__lte=date, completion=True
    )
    #print("week stats: ", week_stats)
    week_stats['avg'] = week_stats['time']/7
    if True:        
        week_log_tags = week_stats['log_tags']
        week_log_dates = week_stats['log_dates']
        week_log_durations = [d/60 for d in week_stats['log_durations']]
        fig = go.Figure(data=[go.Histogram(
            x=week_log_dates, y=week_log_durations,
            histfunc='sum'
        )])
        fig.update_layout(
            title="Last week",
            xaxis_title="Days",
            yaxis_title="Hours",
        )
        img_bytes = fig.to_image(format='svg')
        
        week_stats['plot_bytes'] = urllib.parse.quote(img_bytes.decode('utf-8')) #b64encode(img_bytes).decode('utf-8')
        
        
    ### QUERY
    month_stats = get_stats_for_filters(
        user_id=user_id,tags=True, logs_plot_data=True, date__gte=start_of_month, date__lte=date, completion=True
    )
    #print("month stats", month_stats)
    month_stats['avg'] = month_stats['time']/30
    if True:        
        month_log_tags = month_stats['log_tags']
        month_log_dates = month_stats['log_dates']
        month_log_durations = [d/60 for d in month_stats['log_durations']]
        sorted_dates = sorted(month_log_dates)
        dates = ["Week of {}".format(d-datetime.timedelta(days=d.weekday())) for d in sorted_dates]
        fig = go.Figure(data=[go.Histogram(
            x=dates, y=month_log_durations,
            histfunc='sum'
        )])
        fig.update_layout(
            title="Last month",
            xaxis_title="Weeks",
            yaxis_title="Hours",
        )
        img_bytes = fig.to_image(format='svg')
        
        month_stats['plot_bytes'] = urllib.parse.quote(img_bytes.decode('utf-8'))
        
        
    ### QUERY
    all_stats = get_stats_for_filters(
        user_id=user_id,tags=True, logs_plot_data=False, completion=True
    )
    #print("all stats: ", all_stats)

    
    pct_tasks = 0
    pct_time = 0

    num_completed_tasks_for_today = completed_todays_stats['count']
    num_tasks_for_today = todays_stats['count']
    completed_time_for_today = completed_todays_stats['time']
    time_for_today = todays_stats['time']
    if num_tasks_for_today != 0:
        pct_tasks = round((num_completed_tasks_for_today*100)/num_tasks_for_today, 2)
    else:
        pct_tasks = 100
        
    if time_for_today != 0:
        pct_time = round((completed_time_for_today*100)/time_for_today, 2)
    else:
        pct_time = 100
        
    ### query
    # find all completed 
    dates = (TodoLog.objects
             .filter(user_id=user_id, completion=True)
             .distinct('date')
             .values('date')
             #.annotate(count=models.Count('date'))
             #.values('date')
             )

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

        'week_plot': week_stats['plot_bytes'],
        'month_plot': month_stats['plot_bytes'],
        
        'total_time': get_hr_min(all_stats['time']),
        'avg_total_time': avg_total_time,
        'num_total_days': num_total_days, 
        'streak': streak,
        'tags': [
            ("This day's tags", list(completed_todays_stats['tags'])), 
            ("Last 7 day's tags", list(week_stats['tags'])), 
            ("Last 30 day's tags", list(month_stats['tags'])), 
            ("All tags", list(all_stats['tags']))],
        'week_hours_img': None,
        'month_hours_img': None
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
    start = datetime.datetime.now()
    c_stats = calculate_stats(user_id,date)
    after_calc_stats = datetime.datetime.now()
    
    db_stats = Stats.objects.filter(user_id=user_id,date=date).first()
    after_get_stats = datetime.datetime.now()
    
    if db_stats is None:
        db_stats = Stats(user_id=user_id,date=date, stats=c_stats)
    else:
        db_stats.stats = c_stats
    
    db_stats.save()
    after_save_stats = datetime.datetime.now()
    
    # invalid later stats
    later_stats = Stats.objects.filter(user_id=user_id,date__gt=date)
    after_query_later_stats = datetime.datetime.now()
    for stats in later_stats:
        stats.delete()
    after_delete_later_stats = datetime.datetime.now()

    logging.critical(
        """
        calc stats {}ms
        get stats {}ms
        save stats {}ms
        query later stats {}ms
        delete later stats {}ms
        """.format(
            (after_calc_stats - start).total_seconds()*1000,
            (after_get_stats - after_calc_stats).total_seconds()*1000,
            (after_save_stats - after_get_stats).total_seconds()*1000,
            (after_query_later_stats - after_save_stats).total_seconds()*1000,
            (after_delete_later_stats - after_query_later_stats).total_seconds()*1000
        )
    )
    
    return c_stats


def get_or_cache_stats(user_id,date):
    
    
    queried_stats = Stats.objects.filter(user_id=user_id,date=date).first()
    
    if queried_stats is None:
        calced_stats = init_stats(user_id,date)
    else:
        calced_stats = queried_stats.stats


    return calced_stats


def calculate_cumulative_stats(user_id, tag=None):
    
    
    #fig = go.Figure(data=[go.Histogram(
    #    x=dates, y=month_log_durations,
    #    histfunc='sum'
    #)])
    #fig.update_layout(
    #    title="Last month",
    #    xaxis_title="Weeks",
    #    yaxis_title="Hours",
    #)

    if tag is not None:
        all_stats = get_stats_for_filters(
            completion=True,
            user_id=user_id, tags=False, logs_plot_data=True,
            tag=tag
        )
    else:
        all_stats = get_stats_for_filters(
            completion=True,
            user_id=user_id, tags=False, logs_plot_data=True
        )
        

    log_tags = all_stats['log_tags']
    log_dates = all_stats['log_dates']
    sorted_dates = sorted(log_dates)
    dates = ["Month of {}".format(d.replace(day=1)) for d in sorted_dates]
    log_durations = [d/60 for d in all_stats['log_durations']]
    per_month_fig = go.Figure(data=[
        go.Histogram(
            x=dates,
            y=log_durations,
            histfunc='sum'
        )
    ])
    per_month_fig.update_layout(
        title="Time per month",
        xaxis_title="Months",
        yaxis_title="Hours",
    )



    per_month_count_fig = go.Figure(data=[
        go.Histogram(
            x=dates,
            y=log_tags,
            histfunc='count',
            cumulative_enabled=True,
        )
    ])
    per_month_count_fig.update_layout(
        title="Entries per month",
        xaxis_title="Months",
        yaxis_title="Hours",
    )
    
    cumulative_fig = go.Figure(data=[
        go.Histogram(
            x=dates,
            y=log_durations,
            histfunc='sum',
            cumulative_enabled=True,
        )
    ])
    cumulative_fig.update_layout(
        title="Cumulative Time",
        xaxis_title="Months",
        yaxis_title="Hours",
    )


    cumulative_count_fig = go.Figure(data=[
        go.Histogram(
            x=dates,
            y=log_tags,
            histfunc='count',
            cumulative_enabled=True,
        )
    ])
    cumulative_count_fig.update_layout(
        title="Cumulative Entries",
        xaxis_title="Months",
        yaxis_title="Hours",
    )


    all_tags = [t[0] for t in TodoLog.objects.values_list('tag').distinct()]
    
    return (per_month_fig.to_html(),
            per_month_count_fig.to_html(),
            cumulative_fig.to_html(),
            cumulative_count_fig.to_html(),
            all_tags)

