from django import template

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return value / arg
    except ZeroDivisionError:
        return 0

@register.filter
def multiply(value, arg):
    return value * arg