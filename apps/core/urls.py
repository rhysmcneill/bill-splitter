from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import dashboard_view, SignupView, LoginView

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),


    # Dashboard
    path('business/<slug:business_slug>/', dashboard_view, name='business_dashboard'),
]