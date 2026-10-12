from django.urls import path

from accounts.views import (
    LoginView,
    LogoutView,
    MeView,
    MyOrganizationsView,
    RegisterView,
    SwitchOrganizationView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("organizations/", MyOrganizationsView.as_view(), name="organizations"),
    path("switch-organization/", SwitchOrganizationView.as_view(), name="switch-organization"),
]
