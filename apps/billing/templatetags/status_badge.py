from django import template

register = template.Library()

@register.simple_tag
def status_badge_class(status):
    return {
        'paid': 'bg-green-100 text-green-700',
        'partial': 'bg-yellow-100 text-yellow-700',
        'partial_paid': 'bg-yellow-100 text-yellow-700',
        'unpaid': 'bg-red-100 text-red-700',
    }.get(status, 'bg-gray-100 text-gray-700')
