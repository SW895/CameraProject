from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter
@stringfilter
def get_url(full_url, query_param):
    if full_url.find(query_param) > 0:
        return full_url
    if full_url.find('?') > 0:
        new_url = full_url + '&' + query_param + '=True'
        return new_url
    new_url = full_url + '?' + query_param + '=True'
    return new_url
