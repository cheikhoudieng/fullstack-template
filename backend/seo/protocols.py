from typing import Protocol, Optional, Dict, List
from seo.data import PageContext, StandardizedSEOData
from seo.models import SEOOverride

class SEODataProvider(Protocol):
    def get_seo_data(self, context: PageContext) -> StandardizedSEOData:
        """Extrait les données SEO brutes du contexte et les retourne sous forme standardisée."""
        ...

class SEOGenerator(Protocol):
    def generate(self, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Dict:
        """Génère une partie des données SEO finales (meta, social, json-ld)."""
        ...

class JsonLdGeneratorFunction(Protocol):
     def __call__(self, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict]:
        """Fonction qui génère un type spécifique de JSON-LD."""
        ...