from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Tuple
from django.http import HttpRequest
from decimal import Decimal

@dataclass
class PageContext:
    """Données contextuelles brutes de la requête/vue."""
    request: HttpRequest
    obj: Optional[Any] = None
    page_type: str = 'website' # 'product', 'category', 'search', 'static', etc.
    view_kwargs: Dict[str, Any] = field(default_factory=dict)
    extra_data: Dict[str, Any] = field(default_factory=dict) # Pour breadcrumbs, terme recherche, 

    def get_absolute_uri(self, relative_path: str) -> str:
        return self.request.build_absolute_uri(relative_path)

@dataclass
class StandardizedSEOData:
    """Données SEO extraites et normalisées par un Provider."""
    name: Optional[str] = None          # Titre principal de l'entité (produit, catégorie)
    description: Optional[str] = None   # Description principale
    main_image_url: Optional[str] = None # URL absolue de l'image principale
    url_path: Optional[str] = None      # Chemin relatif pour l'URL canonique/OG
    keywords: List[str] = field(default_factory=list)
    # --- Champs spécifiques E-commerce ---
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    category_name: Optional[str] = None
    availability: Optional[str] = None # Ex: 'InStock', 'OutOfStock'
    sku: Optional[str] = None
    # --- Champs Blog ---
    author_name: Optional[str] = None
    date_published: Optional[str] = None # ISO format
    date_modified: Optional[str] = None  # ISO format
    # --- Autres ---
    breadcrumbs: List[Tuple[str, Optional[str]]] = field(default_factory=list) # List of (Name, path)
    # Ajoutez d'autres champs standardisés si nécessaire
    card_product_list: Optional[List[Dict[str, Any]]] = None # Liste de dicts produit simplifiés
