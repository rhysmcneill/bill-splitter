from django.urls import path
from .views import connect_stripe_view, manage_stripe_account_view, customer_bill_view , \
    choose_payment_mode_view, pay_for_bill, set_payment_mode, check_payment_mode, \
    identify_user_and_choose


urlpatterns = [

    # Initial stripe connection
    path('business/<slug:slug>/connect-stripe/', connect_stripe_view, name='connect_stripe'),
    path('business/<slug:slug>/manage-stripe/', manage_stripe_account_view, name='manage_stripe'),

    path('pay/<uuid:uuid>/', customer_bill_view, name='customer_bill'),

    # Identify customer
    # path("pay/<uuid:uuid>/identify/", identify_participant_modal, name="identify_participant_modal"),
    # path("pay/<uuid:uuid>/identify/submit/", identify_participant_submit, name="identify_participant_submit"),

    path("pay/<uuid:uuid>/choose/", choose_payment_mode_view, name="choose_payment_mode"),
    path("pay/<uuid:uuid>/choose/set-mode/", set_payment_mode, name="set_payment_mode"),  # Updated
    path("pay/<uuid:uuid>/choose/check-mode/", check_payment_mode, name="check_payment_mode"),  # Polling
    path("pay/<uuid:uuid>/", pay_for_bill, name="pay_for_bill"),

    #new
    path("pay/<uuid:uuid>/identify/choose/", identify_user_and_choose, name="identify_user_and_choose"),


]
