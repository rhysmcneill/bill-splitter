from .views import create_bill_view
from django.urls import path

urlpatterns = [
    path('business/<slug:business_slug>/bills/new/', create_bill_view, name='create_bill'),
]
