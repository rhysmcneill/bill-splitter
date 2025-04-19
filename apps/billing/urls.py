from .views import create_bill_view, list_bill_view, delete_bill_view, update_bill_view, view_bill_view, \
    upload_receipt_view
from django.urls import path

urlpatterns = [
    path('business/<slug:business_slug>/bills/', list_bill_view, name='list_bill'),
    path('business/<slug:business_slug>/bills/new/', create_bill_view, name='create_bill'),
    path('business/<slug:business_slug>/bills/delete/<uuid:uuid>/', delete_bill_view, name='delete_bill'),
    path('business/<slug:business_slug>/bills/<uuid:uuid>/update/', update_bill_view, name='update_bill'),
    path('business/<slug:business_slug>/bills/<uuid:uuid>/view/', view_bill_view, name='view_bill'),
    path('ocr/upload/', upload_receipt_view, name='upload-receipt'),
]
