from .views import create_bill_view, list_bill_view, delete_bill_view, update_bill_view, view_bill_view, \
    upload_receipt_view, bill_qr_view, customer_bill_view
from django.urls import path

urlpatterns = [
    # Billing
    path('business/<slug:business_slug>/bills/', list_bill_view, name='list_bill'),
    path('business/<slug:business_slug>/bills/new/', create_bill_view, name='create_bill'),
    path('business/<slug:business_slug>/bills/delete/<uuid:uuid>/', delete_bill_view, name='delete_bill'),
    path('business/<slug:business_slug>/bills/<uuid:uuid>/update/', update_bill_view, name='update_bill'),
    path('business/<slug:business_slug>/bills/<uuid:uuid>/view/', view_bill_view, name='view_bill'),

    # AI
    path('ocr/upload/', upload_receipt_view, name='upload-receipt'),

    # QR / Customer views
    path('business/<slug:business_slug>/bills/<uuid:uuid>/qr/', bill_qr_view, name='bill_qr'),
    path('pay/<uuid:uuid>/', customer_bill_view, name='customer_bill'),

]
