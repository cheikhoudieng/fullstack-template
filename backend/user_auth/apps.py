from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UserAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_auth'
    verbose_name = _("Authentification et Utilisateurs")

    def ready(self):
        import user_auth.signals
