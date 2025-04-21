from django.urls import path
from .views import connect_stripe_view, manage_stripe_account_view, customer_bill_view , identify_participant_modal, \
    identify_participant_submit


urlpatterns = [

    # Initial stripe connection
    path('business/<slug:slug>/connect-stripe/', connect_stripe_view, name='connect_stripe'),
    path('business/<slug:slug>/manage-stripe/', manage_stripe_account_view, name='manage_stripe'),

    path('pay/<uuid:uuid>/', customer_bill_view, name='customer_bill'),

    # Identify customer
    path("pay/<uuid:uuid>/identify/", identify_participant_modal, name="identify_participant_modal"),
    path("pay/<uuid:uuid>/identify/submit/", identify_participant_submit, name="identify_participant_submit"),

]
