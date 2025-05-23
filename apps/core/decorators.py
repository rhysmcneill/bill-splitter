from django.shortcuts import render
from functools import wraps


# Ensure user is making a request for the business they are in, otherwise 403
def business_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'business'):
            return render(request, 'core/error/403.html', status=403)

        # strict check
        if request.user.is_authenticated and request.user.business != request.business:
            return render(request, 'core/error/403.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


# Check if user is admin, otherwise throw 403
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['admin', 'business_owner']:
            return render(request, 'core/error/403.html', status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view