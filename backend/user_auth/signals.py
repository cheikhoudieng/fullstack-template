from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings # Pour le modèle User et d'autres settings
from django.urls import reverse # Si vous voulez inclure un lien de confirmation/login

send_templated_email = None # Gérer le cas où l'import échoue

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=settings.AUTH_USER_MODEL) # Écoute le signal post_save pour le modèle User
def send_welcome_email_on_user_creation(sender, instance, created, **kwargs):
    """
    Envoie un email de bienvenue lorsqu'un nouvel utilisateur est créé.
    """
    if created: # On agit seulement si l'instance vient d'être créée
        
        # Préparer le contexte pour le template email
        # Vous pouvez ajouter d'autres variables utiles ici
        # frontend_login_url = f"{getattr(settings, 'FRONTEND_SITE_URL', 'http://localhost:3000')}/login" # Exemple
        # activation_token = ... # Si vous avez un processus d'activation
        
        context = {
            'user': instance, # L'instance User complète
            'user_name': instance.full_name or instance.username,
            # 'login_url': frontend_login_url, 
            # 'activation_url': ... # Si applicable
            # 'site_name' et 'site_url' sont ajoutés par send_templated_email
        }

        try:
            if send_templated_email is None:
                logger.error("send_templated_email n'est pas disponible. Assurez-vous que le module notifications est installé.")
                return
            send_templated_email(
                subject_template_name='notifications/email/user_auth/welcome_subject.txt',
                html_template_name='notifications/email/user_auth/welcome_body.html',
                text_template_name='notifications/email/user_auth/welcome_body.txt', # Optionnel
                context=context,
                recipient_list=[instance.email],
                event_type='user_welcome_email', # Pour NotificationLog
                recipient_user=instance, # Pour lier le log à cet utilisateur
                related_object=instance # Si vous utilisez GenericForeignKey dans NotificationLog pour l'user
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de bienvenue à {instance.email}: {e}", exc_info=True)