from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .forms import StyledAuthenticationForm, StyledPasswordChangeForm

app_name = "users"

urlpatterns = [
    # --- Pi auth ---
    path("pi/login/", views.pi_login, name="pi_login"),
    
    # Autenticación
    path(
        "login/",
        views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
            authentication_form=StyledAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),

    # Registro y perfil
    path("register/", views.register, name="register"),
    path("profile/",  views.profile,  name="profile"),

    # Descarga de CV (protegida)
    path("cv/",     views.cv_gate,     name="cv_page"),
    path("cv/get/", views.cv_download, name="cv_download"),

    # --- Recuperación de contraseña ---
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/emails/password_reset_email.html",   
            subject_template_name="accounts/emails/password_reset_subject.txt", 
            html_email_template_name=None,                                   
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
            
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # --- Cambio de contraseña (requiere login) ---
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
            form_class=StyledPasswordChangeForm,
            success_url=reverse_lazy("users:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html"
        ),
        name="password_change_done",
    ),
    
]
