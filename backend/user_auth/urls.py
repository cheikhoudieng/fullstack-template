from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from user_auth.views import LoginView, LogoutView, UserProfileView, UserCreateView, GetCSRFToken, CookieTokenRefreshView, LoginFormView, PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('user/', UserProfileView.as_view(), name='user_profile'),
    path('register/', UserCreateView.as_view(), name='register'),
    path('csrf/', GetCSRFToken.as_view(), name='get_csrf'),
    path('login-form/', LoginFormView.as_view(), name='login_form'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request_api'),
    path('password-reset-confirm/<uuid:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm_api'), 
]

