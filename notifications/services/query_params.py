from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def parse_date_param(value, end_of_day=False):
    if not value:
        return None
    parsed_dt = parse_datetime(value)
    if parsed_dt:
        if timezone.is_naive(parsed_dt):
            return timezone.make_aware(parsed_dt)
        return parsed_dt
    parsed_date = parse_date(value)
    if not parsed_date:
        return None
    if end_of_day:
        parsed_dt = timezone.datetime.combine(
            parsed_date,
            timezone.datetime.max.time(),
        )
    else:
        parsed_dt = timezone.datetime.combine(
            parsed_date,
            timezone.datetime.min.time(),
        )
    return timezone.make_aware(parsed_dt) if timezone.is_naive(parsed_dt) else parsed_dt
