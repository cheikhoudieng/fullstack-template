from typing import Dict, Optional
from django.urls import reverse
from seo.protocols import SEODataProvider
from seo.data import PageContext, StandardizedSEOData
from seo.config import seo_config

class BaseDataProvider:
    """Classe de base optionnelle pour partager des logiques."""
    def get_common_data(self, context: PageContext) -> dict:
        return {
            'currency': seo_config.default_currency,
            'breadcrumbs': context.extra_data.get('breadcrumbs', [])
        }



class LoginPageSEODataProvider(BaseDataProvider, SEODataProvider):
    """Fournit les données SEO normalisées pour la page de connexion."""

    def get_seo_data(self, context: PageContext) -> StandardizedSEOData:
        page_title = context.extra_data.get('page_title', "Connexion - Cicaw") # Fallback
        page_description = context.extra_data.get('page_description', "")

        url_path = None
        try:
            # Assurez-vous d'avoir un nom d'URL pour cette vue (ex: 'login')
            url_path = reverse('login') # Remplacer par le nom réel de l'URL de connexion
        except Exception as e:
             print(f"WARN: Impossible de trouver l'URL nommée 'login': {e}")
             url_path = '/login' # Fallback

        common_data = self.get_common_data(context)

        return StandardizedSEOData(
            name=page_title,
            description=page_description,
            url_path=url_path,
            **common_data
        )
    

class SignupPageSEODataProvider(BaseDataProvider, SEODataProvider):
    """Fournit les données SEO normalisées pour la page d'inscription."""

    def get_seo_data(self, context: PageContext) -> StandardizedSEOData:
        page_title = context.extra_data.get('page_title', "Inscription - Cicaw") # Fallback
        page_description = context.extra_data.get('page_description', "")

        url_path = None
        try:
            url_path = reverse('signup') # Assurez-vous que 'signup' est le nom de votre URL
        except Exception as e:
             print(f"WARN: Impossible de trouver l'URL nommée 'signup': {e}")
             url_path = '/sign-in/' # Fallback sur l'URL en dur si vous utilisez celle-là

        common_data = self.get_common_data(context)

        return StandardizedSEOData(
            name=page_title,
            description=page_description,
            url_path=url_path,
            # Pas d'autres données spécifiques ici
            **common_data
        )


# Registre des providers
PROVIDER_REGISTRY: Dict[str, SEODataProvider] = {
    'login_page': LoginPageSEODataProvider(),
    'signup_page': SignupPageSEODataProvider(),
}

def get_provider(page_type: str) -> Optional[SEODataProvider]:
    return PROVIDER_REGISTRY.get(page_type)