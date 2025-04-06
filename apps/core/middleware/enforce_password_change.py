from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        exempt_urls = [
            reverse("logout"),
            reverse("force_password_change"),
        ]

        if user.is_authenticated and user.must_change_password:
            if request.path not in exempt_urls:
                return redirect("force_password_change")

        return self.get_response(request)
