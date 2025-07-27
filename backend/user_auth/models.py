from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

def default_reset_token_expiry():
    return timezone.now() + timedelta(hours=settings.PASSWORD_RESET_TIMEOUT_HOURS 
                                       if hasattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS') else 1)

class User(AbstractUser):
    first_name = None
    last_name = None
    class Sexe(models.TextChoices):
        MALE = 'Homme', 'Homme'
        FEMALE = 'Femme', 'Femme'

    full_name = models.CharField(max_length=255)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=5, choices=Sexe.choices)
    profile_color = models.CharField(max_length=10, default='#362c54')

    def generate_random_color(self):
        letters = '0123456789ABCDEF'
        color = '#'
        is_light_color = True

        # Boucle pour générer une couleur tant que la luminance est trop claire (luminance > 0.7)
        while is_light_color:
            color = '#'
            for i in range(6):
                color += letters[random.randint(0, 15)]  # Choix aléatoire d'un caractère hexadécimal

            # Calcul de la luminance de la couleur pour déterminer si elle est claire ou sombre
            luminance = (0.299 * int(color[1:3], 16) +
                         0.587 * int(color[3:5], 16) +
                         0.114 * int(color[5:7], 16)) / 255

            # Vérification si la couleur est claire (luminance > 0.7)
            is_light_color = luminance > 0.7

        return color
    

class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_reset_token_expiry)
    used_at = models.DateTimeField(null=True, blank=True) # Quand le token a été utilisé

    def is_valid(self):
        return not self.used_at and timezone.now() < self.expires_at

    def mark_as_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])

    def __str__(self):
        return f"Reset token for {self.user.username}"

    class Meta:
        verbose_name = _("Token de Réinitialisation de Mot de Passe")
        verbose_name_plural = _("Tokens de Réinitialisation de Mot de Passe")
        ordering = ['-created_at']


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Appel de la méthode pour générer une couleur aléatoire
        instance.profile_color = instance.generate_random_color()
        instance.save()