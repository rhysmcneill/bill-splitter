from django.urls import path
from .views import connect_stripe_view, manage_stripe_account_view, customer_bill_view , \
    choose_payment_mode_view, pay_for_bill, set_payment_mode, check_payment_mode, \
    identify_user_and_choose, split_equal_view, check_participant_count, participant_list_partial, create_checkout_session, \
    payment_success, split_unequally_view, unequal_shares_partial


urlpatterns = [

    # Initial stripe connection
    path('business/<slug:slug>/connect-stripe/', connect_stripe_view, name='connect_stripe'),
    path('business/<slug:slug>/manage-stripe/', manage_stripe_account_view, name='manage_stripe'),

    # Payment flow views
    path("pay/<uuid:uuid>/choose/", choose_payment_mode_view, name="choose_payment_mode"),
    path("pay/<uuid:uuid>/choose/check-mode/", check_payment_mode, name="check_payment_mode"),  # Polling bill splitter
    path("pay/<uuid:uuid>/", pay_for_bill, name="pay_for_bill"),

    # Equal Split
    path('pay/<uuid:uuid>/split/equal/', split_equal_view, name='equal_split'),
    path('pay/<uuid:uuid>/split/equal/check/', check_participant_count, name='check_participant_count'),  # Polling
    path('pay/<uuid:uuid>/split/equal/participants/', participant_list_partial, name='equal_split_participants'),

    # Unequal
    path('pay/<uuid:uuid>/split/unequal/', split_unequally_view, name='unequal_split'),
    path('pay/<uuid:uuid>/split/unequal/shares/', unequal_shares_partial, name='unequal_shares_partial'),


    path("pay/<uuid:uuid>/identify/choose/", identify_user_and_choose, name="identify_user_and_choose"),
    path('pay/<uuid:uuid>/participant/<int:participant_id>/checkout/', create_checkout_session,
         name='create_checkout_session'),
    path('pay/<uuid:uuid>/participant/<int:participant_id>/success/', payment_success, name='payment_success'),

]
