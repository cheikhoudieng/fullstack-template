from typing import Optional, Dict, List
from seo.protocols import SEOGenerator
from seo.data import PageContext, StandardizedSEOData # MODIFIÉ: Importer PageContext
from seo.models import SEOOverride
from seo.config import seo_config

class SocialTagGenerator(SEOGenerator):

    def _get_value(self, override_value: Optional[str], seo_data_value: Optional[str], default_value: Optional[str] = None) -> Optional[str]:
        """Helper pour obtenir la valeur selon la priorité: override -> seo_data -> default."""
        if override_value:
            return override_value
        if seo_data_value:
            return seo_data_value
        return default_value

    def generate(self, page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Dict: # MODIFIÉ: Accepte page_context
        """Génère les balises meta pour Open Graph et Twitter Cards."""
        og_tags = []
        twitter_tags = []

        # --- URLs Absolues ---
        # Construire l'URL absolue si un path relatif est fourni
        absolute_url = None
        if seo_data.url_path:
            try:
                # Utiliser la requête depuis page_context
                absolute_url = page_context.request.build_absolute_uri(seo_data.url_path)
            except Exception:
                pass # Gérer l'erreur si build_absolute_uri échoue

        canonical_url_from_override = getattr(override, 'canonical_url', None)
        final_url = canonical_url_from_override or absolute_url # Priorité à l'override canonique si défini

        # --- Titres ---
        og_title = self._get_value(
            getattr(override, 'og_title', None),
            seo_data.name, # Utilise le nom principal de l'objet/page comme fallback
            seo_config.default_title # En dernier recours, le titre SEO par défaut
        )
        twitter_title = self._get_value(
            getattr(override, 'twitter_title', None),
            og_title, # Fallback sur le titre OG
            seo_data.name or seo_config.default_title
        )

        # --- Descriptions ---
        og_description = self._get_value(
            getattr(override, 'og_description', None),
            seo_data.description, # Utilise la description principale
            seo_config.default_description # En dernier recours, la description par défaut
        )
        twitter_description = self._get_value(
            getattr(override, 'twitter_description', None),
            og_description, # Fallback sur la description OG
            seo_data.description or seo_config.default_description
        )
         # Tronquer twitter description si nécessaire (max ~200 cars)
        if twitter_description and len(twitter_description) > 200:
             twitter_description = twitter_description[:197] + '...'


        # --- Images ---
        og_image = self._get_value(
            getattr(override, 'og_image', None),
            seo_data.main_image_url, # Utilise l'image principale de l'objet/page
            seo_config.default_og_image # En dernier recours, l'image OG par défaut
        )
        twitter_image = self._get_value(
            getattr(override, 'twitter_image', None),
            og_image, # Fallback sur l'image OG (souvent la même)
            seo_config.default_og_image
        )

        # --- Types & Card ---
        og_type = self._get_value(
            getattr(override, 'og_type', None),
             # On pourrait ajouter 'page_type' à StandardizedSEOData pour déterminer dynamiquement le type OG
             page_context.page_type if page_context.page_type in ['article', 'product'] else None, # Exemple simple
            seo_config.default_og_type
        )
        twitter_card = self._get_value(
            getattr(override, 'twitter_card', None),
             # Logique possible ici si nécessaire, sinon le défaut
            None,
            seo_config.default_twitter_card
        )

        # --- Génération des Tags OG ---
        def add_og(prop, content):
            if content: og_tags.append({'type': 'property', 'name_or_property': f"og:{prop}", 'content': content})

        add_og('title', og_title)
        add_og('description', og_description)
        add_og('image', og_image)
        add_og('type', og_type)
        if final_url: add_og('url', final_url)
        if seo_config.site_name: add_og('site_name', seo_config.site_name)
        if seo_config.default_locale: add_og('locale', seo_config.default_locale)
        # Ajouter tags spécifiques si besoin (ex: product:price:amount, product:price:currency)
        if page_context.page_type == 'product' and seo_data.price is not None:
            add_og('price:amount', str(seo_data.price))
            add_og('price:currency', seo_data.currency or seo_config.default_currency)
        if page_context.page_type == 'product' and seo_data.availability is not None:
             # Convertir la disponibilité simple en URL schema.org si nécessaire
             availability_map = {'InStock': 'https://schema.org/InStock', 'OutOfStock': 'https://schema.org/OutOfStock'}
             og_availability = availability_map.get(seo_data.availability, seo_data.availability)
             add_og('availability', og_availability)


        # --- Génération des Tags Twitter ---
        def add_tw(prop, content):
             if content: twitter_tags.append({'type': 'name', 'name_or_property': f"twitter:{prop}", 'content': content})

        add_tw('card', twitter_card)
        add_tw('title', twitter_title)
        add_tw('description', twitter_description)
        add_tw('image', twitter_image)
        if seo_config.twitter_site: add_tw('site', seo_config.twitter_site)

        return {
            'og_tags': og_tags,
            'twitter_tags': twitter_tags
        }