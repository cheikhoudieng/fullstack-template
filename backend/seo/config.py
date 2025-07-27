# seo/config.py

from django.conf import settings
from typing import Optional, Dict, Any, List # Importer les types nécessaires

class SEOConfig:
    """
    Fournit un accès simple et centralisé aux paramètres SEO globaux
    définis dans settings.SEO_SETTINGS.

    Utilise des propriétés pour récupérer dynamiquement les valeurs des settings
    et fournir des valeurs par défaut raisonnables si une clé n'est pas définie.
    """

    @property
    def settings_dict(self) -> Dict[str, Any]:
        """Accès brut au dictionnaire SEO_SETTINGS si nécessaire."""
        return getattr(settings, 'SEO_SETTINGS', {})

    @property
    def default_title(self) -> str:
        """Titre par défaut pour la balise <title> si aucun titre spécifique n'est généré."""
        return self.settings_dict.get('DEFAULT_TITLE', 'Titre par Défaut') # Rendre le défaut plus évident

    @property
    def title_template(self) -> str:
        """
        Template pour formater les titres des pages (ex: '%s | Nom du Site').
        Le '%s' sera remplacé par le nom spécifique de la page/objet.
        """
        return self.settings_dict.get('TITLE_TEMPLATE', '%s')

    @property
    def default_description(self) -> str:
        """Description par défaut pour la balise <meta name="description">."""
        return self.settings_dict.get('DEFAULT_DESCRIPTION', '')

    @property
    def default_og_image(self) -> Optional[str]:
        """URL absolue de l'image Open Graph par défaut."""
        return self.settings_dict.get('DEFAULT_OG_IMAGE', None)

    @property
    def default_og_type(self) -> str:
        """Type Open Graph par défaut (ex: 'website', 'article', 'product')."""
        return self.settings_dict.get('DEFAULT_OG_TYPE', 'website')

    @property
    def site_name(self) -> str:
        """Nom du site web (utilisé pour og:site_name, etc.)."""
        return self.settings_dict.get('SITE_NAME', '')

    @property
    def twitter_site(self) -> Optional[str]:
        """Handle Twitter du site (ex: '@VotreCompte'). Inclure le '@'."""
        return self.settings_dict.get('TWITTER_SITE', None)

    @property
    def default_robots(self) -> str:
        """Contenu par défaut pour la balise <meta name="robots"> (ex: 'index, follow')."""
        return self.settings_dict.get('DEFAULT_ROBOTS', 'index, follow')

    @property
    def default_locale(self) -> str:
        """Locale par défaut (ex: 'fr_SN', 'en_US') utilisée pour og:locale."""
        # Basé sur votre utilisation précédente
        return self.settings_dict.get('DEFAULT_LOCALE', 'fr_SN')

    @property
    def default_currency(self) -> str:
        """Code devise par défaut (ISO 4217, ex: 'XOF', 'USD', 'EUR')."""
        # Basé sur votre utilisation précédente
        return self.settings_dict.get('DEFAULT_CURRENCY', 'XOF')

    @property
    def default_twitter_card(self) -> str:
         """Type de carte Twitter par défaut (ex: 'summary_large_image', 'summary')."""
         # summary_large_image est souvent un bon défaut pour les marketplaces
         return self.settings_dict.get('DEFAULT_TWITTER_CARD', 'summary_large_image')

    @property
    def default_organization(self) -> Dict[str, Any]:
        """
        Dictionnaire JSON-LD par défaut pour le Schema.org Organization ou Publisher.
        Utilisé comme base pour le JSON-LD du site.
        """
        return self.settings_dict.get('JSONLD_DEFAULT_ORGANIZATION', {})

    @property
    def organization_name(self) -> Optional[str]:
        """Nom de l'organisation extrait de default_organization."""
        return self.default_organization.get('name')

    @property
    def organization_logo(self) -> Optional[str]:
        """URL du logo de l'organisation extrait de default_organization."""
        return self.default_organization.get('logo')

    @property
    def organization_url(self) -> Optional[str]:
         """URL de l'organisation extrait de default_organization."""
         return self.default_organization.get('url')

    @property
    def organization_same_as(self) -> List[str]:
        """Liste des URLs 'sameAs' (profils sociaux) extraite de default_organization."""
        return self.default_organization.get('sameAs', [])

    # --- Ajoutez d'autres propriétés au besoin ---
    # Exemple: Si vous avez une valeur par défaut pour la disponibilité des produits
    # @property
    # def default_availability(self) -> str:
    #     """Disponibilité produit par défaut pour Schema.org (ex: 'https://schema.org/InStock')."""
    #     return self.settings_dict.get('DEFAULT_AVAILABILITY', 'https://schema.org/InStock')


# Instance unique (Singleton) pour une utilisation facile dans toute l'application 'seo'
# Exemple d'utilisation : from seo.config import seo_config -> print(seo_config.site_name)
seo_config = SEOConfig()