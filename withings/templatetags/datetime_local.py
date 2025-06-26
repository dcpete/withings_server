from django import template
from django.utils import formats
import datetime
register = template.Library()


@register.filter(expects_localtime=True, is_safe=False)
def custom_date(value, arg=None):
    if value in (None, ''):
        return ''
    api_date_format = '%Y-%m-%d %H:%M:%S%z'  # 2025-05-08 08:22:00+00:00
    return datetime.datetime.strptime(value, api_date_format)

@register.filter(name='add_time')
def add_time(value):
    print(value)
    return (datetime.datetime(value) + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    