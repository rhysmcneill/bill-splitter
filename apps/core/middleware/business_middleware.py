from django.shortcuts import render
from ..models import Business

class BusinessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        business = None

        # If URL contains /business/<slug>/ → extract slug
        if path.startswith('/business/'):
            parts = path.strip('/').split('/')
            if len(parts) > 1:
                slug = parts[1]
                try:
                    business = Business.objects.get(slug=slug)
                    request.business = business

                    # Optional: tenant ownership check
                    if request.user.is_authenticated:
                        if request.user.business != business:
                            return render(request, 'core/error/403.html', status=403)
                except Business.DoesNotExist:
                    return render(request, 'core/error/404.html', status=404)

        # Fallback for non-tenant routes like '/', '/login', etc.
        elif request.user.is_authenticated:
            business = getattr(request.user, 'business', None)
            request.business = business

        else:
            request.business = None

        return self.get_response(request)
