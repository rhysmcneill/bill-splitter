from django.shortcuts import get_object_or_404, render
from ..models import Business

class BusinessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Only run this logic for URLs that include /business/<slug>/
        if path.startswith('/business/'):
            parts = path.strip('/').split('/')
            if len(parts) > 1:
                slug = parts[1]
                print(slug)
                try:
                    business = Business.objects.get(slug=slug)
                    request.business = business

                    # Tenant ownership check
                    if request.user.is_authenticated:
                        if request.user.business != business:
                            return render(request, 'core/error/403.html', status=403)

                except Business.DoesNotExist:
                    return render(request, 'core/error/404.html', status=404)

        return self.get_response(request)
