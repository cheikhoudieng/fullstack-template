from django.contrib.contenttypes.models import ContentType
from typing import Optional, Dict

from seo.generators.social import SocialTagGenerator
from seo.models import SEOOverride
from seo.data import PageContext, StandardizedSEOData
from seo.providers import get_provider
from seo.generators.meta import MetaTagGenerator
# from .generators.social import SocialTagGenerator # À créer
from seo.generators.jsonld import JsonLdProcessor

class OverrideService:
    def get_override(self, context: PageContext) -> Optional[SEOOverride]:
        override = None
        if context.obj:
            try:
                ct = ContentType.objects.get_for_model(context.obj.__class__)
                override = SEOOverride.objects.filter(content_type=ct, object_id=context.obj.pk).first()
            except ContentType.DoesNotExist: pass
        if not override and context.request.path:
             override = SEOOverride.objects.filter(path=context.request.path).first()
        return override
    

class SEOOrchestrator:
    def __init__(self):
        self.override_service = OverrideService()
        self.provider_registry = get_provider
        self.meta_generator = MetaTagGenerator()
        self.social_generator = SocialTagGenerator()
        self.jsonld_processor = JsonLdProcessor()

    def get_seo_context(self, page_context: PageContext) -> Dict:
        provider = self.provider_registry(page_context.page_type)
        seo_data = StandardizedSEOData() # Default empty data
        if provider:
            seo_data = provider.get_seo_data(page_context)
            # Note: Pas besoin d'injecter 'request' ici si on passe page_context

        override = self.override_service.get_override(page_context)

        # 3. Générer les différentes parties - MODIFIÉ: Passe page_context
        meta_results = self.meta_generator.generate(page_context, seo_data, override)
        social_results = self.social_generator.generate(page_context, seo_data, override) # MODIFIÉ
        json_ld_scripts = self.jsonld_processor.generate(page_context, seo_data, override) # MODIFIÉ

        # 4. Assembler le contexte final pour le template
        final_context = {
            'title': meta_results.get('title'),
            'canonical': meta_results.get('canonical'), # Devrait maintenant avoir une valeur si url_path fourni
            'meta_tags': [],
            'json_ld': json_ld_scripts, # Devrait maintenant avoir du contenu si configuré
        }

        # Ajouter meta description et robots
        if meta_desc := meta_results.get('meta_description'):
            final_context['meta_tags'].append({'type': 'name', 'name_or_property': 'description', 'content': meta_desc})
        if robots := meta_results.get('robots'):
             final_context['meta_tags'].append({'type': 'name', 'name_or_property': 'robots', 'content': robots})

        # Ajouter les tags OG et Twitter - MODIFIÉ: Décommenter
        final_context['meta_tags'].extend(social_results.get('og_tags', []))
        final_context['meta_tags'].extend(social_results.get('twitter_tags', []))

        return final_context