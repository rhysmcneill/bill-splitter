from django.urls import path
from .views import connect_stripe_view, manage_stripe_account_view

urlpatterns = [

    # Initial stripe connection
     path('business/<slug:slug>/connect-stripe/', connect_stripe_view, name='connect_stripe'),
     path('business/<slug:slug>/manage-stripe/', manage_stripe_account_view, name='manage_stripe'),

]