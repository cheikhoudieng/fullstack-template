from seo.protocols import SEOGenerator
from seo.data import PageContext, StandardizedSEOData
from seo.models import SEOOverride
from seo.config import seo_config
from typing import Optional, Dict

class MetaTagGenerator(SEOGenerator):
    def generate(self, page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Dict:
        # 1. Title
        title = seo_config.default_title
        if override and override.title:
            title = override.title
        elif seo_data.name:
            try:
                title = seo_config.title_template % seo_data.name
            except TypeError:
                title = seo_data.name # Fallback si template invalide

        # 2. Description
        description = seo_config.default_description
        if override and override.meta_description:
            description = override.meta_description
        elif seo_data.description:
            description = seo_data.description # TODO: Tronquer à ~160 caractères

        # 3. Canonical URL
        canonical_url = None
       
        if override and override.canonical_url:
            canonical_url = override.canonical_url
        elif seo_data.url_path:
            try:
                # MODIFIÉ: Utiliser request depuis page_context
                canonical_url = page_context.request.build_absolute_uri(seo_data.url_path)
            except Exception as e:
                # Logguer l'erreur potentielle ici si nécessaire
                print(f"Erreur build_absolute_uri pour canonical: {e}")
                pass # Garder canonical_url = None

        robots = seo_config.default_robots
        if override and override.robots_meta:
            robots = override.robots_meta


        return {
            'title': title,
            'meta_description': description,
            'canonical': canonical_url, # Sera l'URL absolue ou None
            'robots': robots,
        }