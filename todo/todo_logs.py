from .models import TodoLog


def get_logs_for_date(user_id, date, sort_by=None):
    if sort_by:
        return TodoLog.objects.filter(user_id=user_id, date=date).order_by(sort_by)
    else:
        return TodoLog.objects.filter(user_id=user_id, date=date)
    
