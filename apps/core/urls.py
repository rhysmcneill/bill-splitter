from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import dashboard_view, SignupView, LoginView, landing_view, business_settings_view, \
    update_business_info_view, team_management_view, invite_team_member_view, force_password_change_view, \
    remove_team_member_view, change_user_role_view, update_profile_view

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),

    # Users
    path('business/<slug:slug>/team/invite', invite_team_member_view, name='invite_team_member'),
    path('password-change/', force_password_change_view, name='force_password_change'),
    path("business/<slug:slug>/team/<int:user_id>/remove/", remove_team_member_view, name="remove_team_member"),
    path("business/<slug:slug>/team/<int:user_id>/change-role/", change_user_role_view, name="change_user_role"),
    path("business/<slug:slug>/team/update-profile/", update_profile_view, name="update_profile"),


    # Dashboard
    path('business/<slug:business_slug>/', dashboard_view, name='business_dashboard'),
    path('business/<slug:slug>/settings/', business_settings_view, name='business_settings'),

    # Landing
    path('', landing_view, name='landing'),

    # Business Settings
    path('business/<slug:slug>/update/', update_business_info_view, name='update_business_info'),
    path('business/<slug:slug>/team/', team_management_view, name='team_management'),

]
