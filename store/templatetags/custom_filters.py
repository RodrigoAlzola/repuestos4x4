from django import template

register = template.Library()

@register.filter
def currency_format(value):
    try:
        value = float(value)
        value = int(value)
        return f"{value:,}".replace(',', '.')
    except (ValueError, TypeError):
        return value