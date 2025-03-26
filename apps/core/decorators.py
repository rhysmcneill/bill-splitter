from django.shortcuts import render
from functools import wraps


def business_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'business'):
            return render(request, 'core/403.html', status=403)

        # strict check
        if request.user.is_authenticated and request.user.business != request.business:
            return render(request, 'core/403.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
