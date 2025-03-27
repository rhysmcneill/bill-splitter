from .views import create_bill_view, bill_list_view, delete_bill_view
from django.urls import path

urlpatterns = [
    path('business/<slug:business_slug>/bills/new/', create_bill_view, name='create_bill'),
    path('business/<slug:business_slug>/bills/', bill_list_view, name='bill_list'),
    path('business/<slug:business_slug>/bills/delete/<uuid:uuid>/', delete_bill_view, name='delete_bill'),

]
