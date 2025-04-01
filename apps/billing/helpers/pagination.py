from django.core.paginator import Paginator
from typing import Tuple


def paginate_queryset(request, queryset, per_page=10) -> Tuple[object, str]:
    """
    Paginate a queryset and return:
    - page_obj: a Paginator page object
    - querystring: cleaned query string (without `page`) for links
    """
    querydict = request.GET.copy()
    querydict.pop('page', None)
    querystring = querydict.urlencode()

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return page_obj, querystring
