from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, escape
from django.utils.translation import gettext_lazy as _
from .models import SEOOverride # Attention à l'import relatif '.' si dans admin_utils.py

def get_seo_override_link(obj):
    """Génère un lien vers l'ajout ou la modification d'un SEOOverride pour l'objet donné."""
    if not obj or not obj.pk:
        # On ne peut pas créer de lien si l'objet n'est pas encore sauvegardé
        return _("Sauvegarder l'objet d'abord pour gérer le SEO spécifique")

    try:
        content_type = ContentType.objects.get_for_model(obj.__class__)
        override = SEOOverride.objects.filter(content_type=content_type, object_id=obj.pk).first()

        if override:
            url = reverse('admin:seo_seooverride_change', args=[override.pk])
            link_text = _("Voir/Modifier l'Override SEO")
            css_class = "button default"
        else:
            url = reverse('admin:seo_seooverride_add') + f'?content_type={content_type.pk}&object_id={obj.pk}'
            link_text = _("Créer un Override SEO")
            css_class = "button" # Style "Ajouter"

        # Ouvrir dans un nouvel onglet peut être pratique
        return format_html('<a href="{}" class="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, css_class, link_text)

    except ContentType.DoesNotExist:
        print(f"ERROR: ContentType non trouvé pour le modèle {obj.__class__}")
        return _("Erreur : ContentType non trouvé")
    except NoReverseMatch as e:
         print(f"ERROR: NoReverseMatch pour le lien SEO. Vérifiez les noms d'URL admin ('admin:seo_seooverride_change' ou 'add'). Erreur: {e}")
         return _("Erreur : URL admin SEO introuvable")
    except Exception as e:
        print(f"ERROR: Erreur imprévue lors de la génération du lien SEO pour {obj}: {e}")
        return _("Erreur lors de la génération du lien SEO")

# Configuration pour l'admin (si utilisée directement dans list_display)
# get_seo_override_link.short_description = _('SEO Override')
# get_seo_override_link.allow_tags = True # Pour ancien Django, préférer format_html