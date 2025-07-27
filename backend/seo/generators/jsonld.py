import json
from typing import Optional, Dict, List, Callable, Any, Protocol

from django.urls import reverse # Ajout de Any et Protocol
from seo.protocols import JsonLdGeneratorFunction # Assumant que vous l'avez défini quelque part
from seo.data import PageContext, StandardizedSEOData
from seo.models import SEOOverride
from seo.config import seo_config
from decimal import Decimal # Pour typer price

class JsonLdGeneratorFunction(Protocol):
    """Interface pour une fonction qui génère un dictionnaire JSON-LD."""
    def __call__(self, page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
        ...


def generate_website_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma WebSite avec la Sitelinks Search Box."""
    org_url = seo_config.organization_url
    if not org_url:
        print("WARN: SEOConfig.organization_url non défini, WebSite JSON-LD ne sera pas généré.")
        return None

    # Assurez-vous que l'URL est absolue
    try:
        base_url = page_context.request.build_absolute_uri('/')
        if not base_url: # Sécurité si build_absolute_uri retourne None ou vide
             raise ValueError("Impossible de déterminer l'URL de base")
    except Exception as e:
         print(f"WARN: Impossible de construire l'URL absolue pour WebSite JSON-LD: {e}")
         return None

    # Recherche Sitelinks
    search_target_url = page_context.request.build_absolute_uri("/search?q={search_term_string}")
    search_action = {
        "@type": "SearchAction",
        "target": {
            "@type": "EntryPoint",
            "urlTemplate": search_target_url
        },
        "query-input": {
             "@type": "PropertyValueSpecification",
             "valueRequired": True,
             "valueName": "search_term_string"
        }
    }

    website_data = {
         "@context": "https://schema.org",
         "@type": "WebSite",
         "name": seo_config.site_name or seo_config.organization_name or "Cicaw",
         "url": base_url,
         "potentialAction": search_action,
         "publisher": {
              "@type": "Organization",
              "name": seo_config.organization_name or "Cicaw",
              "logo": {
                   "@type": "ImageObject",
                   "url": seo_config.organization_logo
                } if seo_config.organization_logo else None,
              "url": seo_config.organization_url # Utiliser l'URL spécifique de l'orga si différente de celle du site
         } if seo_config.organization_name else None,
          "inLanguage": seo_config.default_locale.split('_')[0] if seo_config.default_locale else "fr" # Ex: 'fr'
    }
    # Filtrer les clés None dans le publisher pour la propreté
    if website_data.get('publisher'):
        website_data['publisher'] = {k:v for k, v in website_data['publisher'].items() if v is not None}
        if website_data['publisher'].get('logo') is None:
             del website_data['publisher']['logo'] # Enlever clé logo si URL est None
        if not website_data.get('publisher'): # Si publisher est devenu vide
             del website_data['publisher']

    return website_data

def generate_organization_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma Organization basé sur la configuration."""
    org_config = seo_config.default_organization
    if not org_config or not org_config.get('name') or not org_config.get('url'):
        print("WARN: Données d'organisation incomplètes dans SEO_SETTINGS, Organization JSON-LD ne sera pas généré.")
        return None

    # Préparer une copie avec @context
    org_data = org_config.copy()
    org_data['@context'] = "https://schema.org"

    # Optionnel: formater le logo en ImageObject si juste une URL est fournie
    if isinstance(org_data.get('logo'), str):
        org_data['logo'] = {"@type": "ImageObject", "url": org_data['logo']}

    return org_data



def generate_product_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """
    Génère le schéma Product complet et optimisé pour Cicaw.
    """
    # --- Validation Essentielle ---
    error_prefix = f"Product JSON-LD generation skipped for product '{seo_data.name or 'UNKNOWN'}' because:"
    if not seo_data.name:
        print(f"{error_prefix} 'name' is missing.")
        return None
    if seo_data.price is None or not isinstance(seo_data.price, (Decimal, float, int)) or seo_data.price < 0:
        print(f"{error_prefix} 'price' is missing, invalid, or negative ('{seo_data.price}').")
        return None
    if not seo_data.url_path:
        print(f"{error_prefix} 'url_path' is missing.")
        return None

    # --- Préparation des Données ---
    try:
        product_url = page_context.request.build_absolute_uri(seo_data.url_path)
        if not product_url: raise ValueError("URL Produit vide générée")
    except Exception as e:
        print(f"ERROR {error_prefix} failed to build absolute URL from '{seo_data.url_path}': {e}")
        return None

    # URLs Images (Liste, image principale en premier)
    image_list = []
    if seo_data.main_image_url:
        image_list.append(seo_data.main_image_url)
    # Ajouter les autres images si elles sont fournies par le provider dans seo_data.image_urls (qui est une List[str])
    if hasattr(seo_data, 'image_urls') and isinstance(seo_data.image_urls, list):
        for img_url in seo_data.image_urls:
            if img_url and img_url != seo_data.main_image_url: # Éviter doublons
                image_list.append(img_url)
    # Utiliser la liste si elle contient plusieurs images, sinon juste la principale
    product_image_data = image_list if len(image_list) > 1 else seo_data.main_image_url

    # Disponibilité
    availability_schema = 'https://schema.org/InStock' # Défaut optimiste
    if seo_data.availability:
        availability_map = { # Case-insensitive matching
            'instock': 'https://schema.org/InStock',
            'outofstock': 'https://schema.org/OutOfStock',
            'preorder': 'https://schema.org/PreOrder',
            'onlineonly': 'https://schema.org/OnlineOnly',
            'limitedavailability': 'https://schema.org/LimitedAvailability',
        }
        lookup_key = str(seo_data.availability).lower().replace(' ', '')
        mapped_url = availability_map.get(lookup_key)

        if mapped_url:
            availability_schema = mapped_url
        elif seo_data.availability.startswith('https://schema.org/'):
             availability_schema = seo_data.availability # Accepter URL directe

    # Marque (Utilisation du nom de la boutique comme fallback)
    brand_data = None
    # if seo_data.brand: # Si le provider a explicitement trouvé une marque
    #      brand_data = {"@type": "Brand", "name": seo_data.brand}
    # if seo_data.shop.name: # Sinon, fallback sur le nom de la boutique
    #      brand_data = {"@type": "Organization", "name": seo_data.shop_name} # Préciser que c'est l'organisation vendeur

    # Seller (Utiliser les infos de la boutique)
    seller_data = None
    # if seo_data.shop_name:
    #     seller_data = {
    #         "@type": "Organization", # ou "Person" si c'est un vendeur individuel sans nom de boutique
    #         "name": seo_data.shop_name,
    #         # Ajouter l'URL de la boutique si fournie par le provider
    #         "url": page_context.request.build_absolute_uri(seo_data.shop_url) if hasattr(seo_data, 'shop_url') and seo_data.shop_url else None
    #     }

    # AggregateRating (Calculé par le Provider)
    aggregate_rating_data = None
    if hasattr(seo_data, 'rating_value') and hasattr(seo_data, 'rating_count') and seo_data.rating_count > 0:
         # S'assurer que rating_value est un nombre valide (ex: "4.5")
         rating_value_str = None
         if isinstance(seo_data.rating_value, (Decimal, float, int)):
             rating_value_str = f"{seo_data.rating_value:.1f}" # Format avec 1 décimale
         elif isinstance(seo_data.rating_value, str):
             try:
                 rating_value_str = f"{float(seo_data.rating_value):.1f}"
             except ValueError:
                 pass # Ignorer si ce n'est pas un nombre

         if rating_value_str is not None:
             aggregate_rating_data = {
                 "@type": "AggregateRating",
                 "ratingValue": rating_value_str,
                 "reviewCount": seo_data.rating_count,
                 # "bestRating": "5", # Optionnel: note max possible
                 # "worstRating": "1" # Optionnel: note min possible
             }

    # Reviews (Formatées par le Provider)
    review_data = None
    if hasattr(seo_data, 'reviews') and isinstance(seo_data.reviews, list) and seo_data.reviews:
         review_data = []
         for review_item in seo_data.reviews:
             # S'assurer que l'item a les clés minimales requises
             if isinstance(review_item, dict) and review_item.get('author_name') and review_item.get('rating_value'):
                 formatted_review = {
                     "@type": "Review",
                     "author": {
                         "@type": "Person", # ou Organization
                         "name": review_item.get('author_name')
                     },
                     "reviewRating": {
                         "@type": "Rating",
                         "ratingValue": str(review_item.get('rating_value')), # Assurer que c'est une string
                         # "bestRating": "5",
                         # "worstRating": "1",
                     },
                     "reviewBody": review_item.get('comment'), # Peut être None/vide
                     "datePublished": review_item.get('date_published'), # Format ISO 8601 YYYY-MM-DD attendu par le provider
                     # "publisher": seller_data # Lier au vendeur/organisation ? Optionnel
                 }
                 # Nettoyer le publisher dans l'auteur et le rating avant de les ajouter
                 if formatted_review['author']:
                    formatted_review['author'] = {k:v for k, v in formatted_review['author'].items() if v is not None}
                 if formatted_review['reviewRating']:
                    formatted_review['reviewRating'] = {k:v for k, v in formatted_review['reviewRating'].items() if v is not None}

                 review_data.append({k:v for k, v in formatted_review.items() if v is not None}) # Nettoyer review individuelle

         if not review_data: # Si la liste est vide après formatage/nettoyage
             review_data = None


    # --- Assemblage Final du Schéma Product ---
    product_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": seo_data.name,
        "description": seo_data.description,
        "image": product_image_data, # Peut être une string (URL) ou une liste d'URLs
        "url": product_url,
        "sku": seo_data.sku, # Sera None si non fourni
        "category": seo_data.category_name, # Nom de la catégorie texte
        "keywords": ", ".join(seo_data.keywords) if seo_data.keywords else None, # Liste -> chaîne séparée par virgules
        "brand": brand_data, # Peut être la marque ou l'organisation fallback
        "itemCondition": "https://schema.org/NewCondition", # Supposer neuf pour une marketplace, à adapter si besoin
        # --- Offre ---
        "offers": {
            "@type": "Offer",
            "url": product_url,
            "price": str(seo_data.price),
            "priceCurrency": seo_data.currency or seo_config.default_currency,
            "availability": availability_schema,
            "itemCondition": "https://schema.org/NewCondition", # Répéter ici est bien vu par certains validateurs
            # "seller": seller_data, # Informations sur le vendeur
            # TODO: Ajouter priceValidUntil, shippingDetails, hasMerchantReturnPolicy ici si dispo dynamiquement
        },
        # --- Avis ---
        "aggregateRating": aggregate_rating_data, # Sera None si pas de données
        "review": review_data, # Sera None si pas de données
    }

    # --- Nettoyage Final (Enlever les clés avec valeurs None/vides) ---
    # Attention: Ne pas enlever "offers" même s'il manque des sous-clés
    # On enlève aussi les listes et dict vides.
    final_data = {k: v for k, v in product_data.items() if v not in [None, [], {}]}

    # Re-vérifier 'brand' et 'seller' dans 'offers' pour propreté
    if 'offers' in final_data:
        if final_data['offers'].get('seller'):
            final_data['offers']['seller'] = {k:v for k,v in final_data['offers']['seller'].items() if v is not None}
            if not final_data['offers']['seller']: # Si seller devient vide
                del final_data['offers']['seller']
        if not final_data['offers']: # Si offers est devenu vide
            del final_data['offers'] # Ne devrait pas arriver avec price/currency/availability

    return final_data

def generate_breadcrumb_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma BreadcrumbList."""
    if not seo_data.breadcrumbs:
        return None

    items = []
    try:
        for i, (name, path) in enumerate(seo_data.breadcrumbs):
             item_data = {
                 "@type": "ListItem",
                 "position": i + 1,
                 "name": name,
             }
             # Ajouter 'item' uniquement si un path est fourni
             if path:
                 item_url = page_context.request.build_absolute_uri(path)
                 if item_url:
                     item_data["item"] = item_url
                 else:
                      print(f"WARN: Impossible de générer URL pour breadcrumb item '{name}' avec path '{path}'")
             items.append(item_data)

        if not items: # Si aucun item n'a pu être généré
             return None

    except Exception as e:
         print(f"ERROR: Échec de la génération des items Breadcrumb: {e}")
         return None

    return {
         "@context": "https://schema.org",
         "@type": "BreadcrumbList",
         "itemListElement": items
    }

def generate_category_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère un schéma de base pour une page de catégorie (pourrait être CollectionPage)."""
    if not seo_data.name or not seo_data.url_path:
        return None

    try:
        category_url = page_context.request.build_absolute_uri(seo_data.url_path)
        if not category_url: raise ValueError("URL Catégorie vide")
    except Exception as e:
         print(f"WARN: Impossible de construire l'URL absolue pour Category JSON-LD: {e}")
         return None

    # Utiliser CollectionPage ou WebPage comme type? WebPage est plus simple.
    category_data = {
        "@context": "https://schema.org",
        "@type": "WebPage", # Ou CollectionPage si vous listez les produits
        "name": seo_data.name,
        "url": category_url,
        "description": seo_data.description,
        "isPartOf": { # Lier au site principal
             "@type": "WebSite",
             "url": seo_config.organization_url or page_context.request.build_absolute_uri('/'),
             "name": seo_config.site_name
        } if seo_config.site_name else None
    }
    return {k: v for k, v in category_data.items() if v is not None}


def generate_card_page_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma CollectionPage pour une page Card."""
    if not seo_data.name or not seo_data.url_path:
        print(f"WARN: Données manquantes (name ou url_path) pour Card Page JSON-LD.")
        return None

    try:
        page_url = page_context.request.build_absolute_uri(seo_data.url_path)
        if not page_url: raise ValueError("URL Page Card vide générée")
    except Exception as e:
        print(f"ERROR Card Page JSON-LD: Impossible de construire l'URL absolue: {e}")
        return None

    item_list_elements = []
    if seo_data.card_product_list: # Utiliser le champ spécifique ajouté
        for i, product_info in enumerate(seo_data.card_product_list):
             # Créer un schéma Product concis pour chaque item de la liste
             product_item_data = {
                 "@type": "Product",
                 "name": product_info.get('name'),
                 "url": product_info.get('url'),
                 "image": product_info.get('image'),
                 "offers": {
                     "@type": "Offer",
                     "price": product_info.get('price'),
                     "priceCurrency": product_info.get('currency'),
                     # Pas besoin de disponibilité ou vendeur ici, c'est juste un aperçu dans la collection
                 } if product_info.get('price') and product_info.get('currency') else None
             }
             # Nettoyer le product_item_data
             product_item_data_clean = {k:v for k,v in product_item_data.items() if v is not None}
             if product_item_data_clean.get('offers') is None:
                 if 'offers' in product_item_data_clean: del product_item_data_clean['offers']

             # Créer le ListItem
             list_item = {
                 "@type": "ListItem",
                 "position": i + 1,
                 "item": product_item_data_clean # Intégrer le Product simplifié
             }
             item_list_elements.append(list_item)

    collection_data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage", # Page listant une collection
        "name": seo_data.name, # Titre de la Card comme nom de la page
        "url": page_url,
        "description": seo_data.description, # Description de la Card
        "isPartOf": { # Lier au site principal
             "@type": "WebSite",
             "url": seo_config.organization_url or page_context.request.build_absolute_uri('/'),
             "name": seo_config.site_name
        } if seo_config.site_name else None,
        "about": { # Décrire l'entité "Card" elle-même
             "@type": "CreativeWork", # Une "œuvre créative" / un regroupement
             "name": seo_data.name,
             "description": seo_data.description,
             "keywords": ", ".join(seo_data.keywords) if seo_data.keywords else None,
             # "url": page_url # L'URL de la page est aussi l'URL "canonique" de cette Card
        },
        # Inclure la liste des éléments si elle n'est pas vide
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(item_list_elements),
            "itemListElement": item_list_elements
        } if item_list_elements else None
        # Alternativement à mainEntity, on pourrait utiliser "hasPart": [ {product_item_data_clean}, ... ]
        # Mais ItemList est plus structuré pour une collection visible.
    }

    return {k:v for k,v in collection_data.items() if v is not None}


def generate_webpage_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère un schéma WebPage simple pour les pages statiques ou génériques."""
    if not seo_data.name or not seo_data.url_path:
        return None

    try:
        page_url = page_context.request.build_absolute_uri(seo_data.url_path)
        if not page_url: raise ValueError("URL Page vide générée")
    except Exception as e:
        print(f"ERROR WebPage JSON-LD: Impossible de construire l'URL absolue: {e}")
        return None

    webpage_data = {
        "@context": "https://schema.org",
        "@type": "WebPage", # Pourrait être un type plus spécifique comme AboutPage, ContactPage si pertinent
        "name": seo_data.name,
        "url": page_url,
        "description": seo_data.description,
        "isPartOf": { # Lier au site principal
             "@type": "WebSite",
             "url": seo_config.organization_url or page_context.request.build_absolute_uri('/'),
             "name": seo_config.site_name
        } if seo_config.site_name else None,
         "inLanguage": seo_config.default_locale.split('_')[0] if seo_config.default_locale else "fr"
        # Optionnel: ajouter 'mainEntity' si la page a un contenu principal spécifique
        # Optionnel: ajouter 'about' si la page parle d'une entité spécifique (ex: l'entreprise)
    }
    return {k:v for k,v in webpage_data.items() if v is not None}


def generate_blog_schema_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma Blog (décrivant le blog en tant qu'entité)."""

    # URL du blog principal (pas la page liste spécifique si elles sont différentes)
    try:
        # Utiliser le même path que la liste, ou définir une URL spécifique pour le blog?
        blog_url = page_context.request.build_absolute_uri(seo_data.url_path or '/blog/')
        if not blog_url: raise ValueError("URL Blog vide")
    except Exception:
        blog_url = seo_config.organization_url or page_context.request.build_absolute_uri('/')
        blog_url = f"{blog_url.strip('/')}/blog/" # Fallback un peu hasardeux

    blog_data = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": seo_data.name or "Blog Cicaw", # Titre de la page liste comme nom du blog
        "url": blog_url,
        "description": seo_data.description,
        "publisher": { # Qui publie ce blog ? L'organisation principale.
             "@type": "Organization",
             "name": seo_config.organization_name,
             "url": seo_config.organization_url,
             "logo": { "@type": "ImageObject", "url": seo_config.organization_logo } if seo_config.organization_logo else None
        } if seo_config.organization_name and seo_config.organization_url else None,
         "inLanguage": seo_config.default_locale.split('_')[0] if seo_config.default_locale else "fr"
        # On pourrait ajouter ici "blogPost": [...] avec un aperçu des X derniers posts
        # si le provider les mettait dans seo_data (ex: dans un champ dédié)
        # "blogPost": [
        #     { "@type": "BlogPosting", "headline": "...", "url": "..." }, ...
        # ]
    }
    final_data = {k:v for k, v in blog_data.items() if v is not None}
    if final_data.get('publisher'):
        final_data['publisher'] = {k:v for k, v in final_data['publisher'].items() if v is not None}
        if not final_data['publisher']: del final_data['publisher']
        if final_data['publisher'].get('logo') is None:
            if 'logo' in final_data['publisher']: del final_data['publisher']['logo']


    return final_data



def generate_blog_posting_ld(page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> Optional[Dict[str, Any]]:
    """Génère le schéma BlogPosting (ou Article) pour un article de blog."""
    if not seo_data.name or not seo_data.url_path or not seo_data.date_published:
        print(f"WARN: Données manquantes (name, url_path ou date_published) pour BlogPosting JSON-LD.")
        return None

    try:
        post_url = page_context.request.build_absolute_uri(seo_data.url_path)
        if not post_url: raise ValueError("URL Article vide")
    except Exception as e:
        print(f"ERROR BlogPosting JSON-LD: Impossible de construire l'URL absolue: {e}")
        return None

    # Précision sur l'auteur
    author_data = {
        "@type": "Person", # Ou 'Organization' si l'auteur est générique
        "name": seo_data.author_name or "Équipe Cicaw"
        # Idéalement ajouter "url": URL_PROFIL_AUTEUR si disponible
    }

    # Organisation éditrice (Publisher)
    publisher_data = None
    if seo_config.organization_name and seo_config.organization_url:
        publisher_data = {
            "@type": "Organization",
            "name": seo_config.organization_name,
            "url": seo_config.organization_url,
            "logo": { "@type": "ImageObject", "url": seo_config.organization_logo } if seo_config.organization_logo else None
        }
        if publisher_data.get('logo') is None:
             if 'logo' in publisher_data: del publisher_data['logo']

    # Image principale
    image_data = None
    if seo_data.main_image_url:
         # On peut fournir juste l'URL ou un objet ImageObject plus détaillé
         image_data = {
             "@type": "ImageObject",
             "url": seo_data.main_image_url,
             # Ajouter "width" et "height" si connus et fournis par le provider
         }
         # Alternative simple : image_data = seo_data.main_image_url


    posting_data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting", # Ou "Article", "NewsArticle" selon la nature
        "mainEntityOfPage": { # Lie cet article à l'URL canonique
            "@type": "WebPage",
            "@id": post_url
         },
        "headline": seo_data.name, # Titre de l'article
        "description": seo_data.description, # Résumé ou début d'article
        "image": image_data, # Image principale (URL ou ImageObject)
        "url": post_url, # URL canonique
        "datePublished": seo_data.date_published, # Format ISO 8601 (YYYY-MM-DD ou avec T Z)
        "dateModified": seo_data.date_modified or seo_data.date_published, # Date modif, fallback sur publication
        "author": author_data,
        "publisher": publisher_data,
        "keywords": ", ".join(seo_data.keywords) if seo_data.keywords else None, # Tags comme keywords
        "articleSection": seo_data.category_name, # Catégorie principale
         "inLanguage": seo_config.default_locale.split('_')[0] if seo_config.default_locale else "fr",
        "isPartOf": { # Fait partie du blog global
            "@type": "Blog", # Lier au schéma Blog (s'il est aussi généré)
            "name": "Blog Cicaw", # Nom cohérent
            "url": page_context.request.build_absolute_uri(reverse('blog_list')) if 'blog_list' in page_context.request.resolver_match.app_name else page_context.request.build_absolute_uri('/blog'), # URL du blog
            "publisher": publisher_data # Editeur du blog
        }

        # Optionnel: Ajouter 'wordCount', 'speakable', etc. si pertinent
    }

    return {k:v for k, v in posting_data.items() if v is not None}


# --- Registre des générateurs JSON-LD ---
JSONLD_GENERATOR_FUNCTIONS: Dict[str, JsonLdGeneratorFunction] = {
    ''
    'website': generate_website_ld,
    'organization': generate_organization_ld,
    'product': generate_product_ld,
    'breadcrumb': generate_breadcrumb_ld,
    'category': generate_category_ld,
    'card_page': generate_card_page_ld,
    'webpage': generate_webpage_ld,
    'blog_schema': generate_blog_schema_ld,
    'blog_posting': generate_blog_posting_ld,
}

# --- Mapper Type de Page aux Schémas à Générer ---
JSONLD_FOR_PAGE_TYPE: Dict[str, List[str]] = {
    'website': ['website', 'organization'], 
    'home': ['website', 'organization'],
    'product': ['product', 'breadcrumb', 'website'],
    'category': ['category', 'breadcrumb', 'website'], 
    'search': ['website'],
    'login': ['website'],
    'cart': ['website'],
    'card': ['card_page', 'breadcrumb', 'website'],
    'seller_landing': ['webpage', 'breadcrumb', 'website', 'organization'],
    'login_page' : ['webpage', 'breadcrumb', 'website', 'organization'],
    'signup_page' : ['webpage', 'breadcrumb', 'website', 'organization'],
    'blog_list_page': ['webpage', 'blog_schema', 'breadcrumb', 'website', 'organization'],
    'blog_post_page' : ['blog_posting', 'breadcrumb', 'website', 'organization'],
    'custom_page': ['webpage', 'breadcrumb', 'website', 'organization']
}


# --- Processeur Principal ---
class JsonLdProcessor:
    """Génère les scripts JSON-LD pour un contexte donné."""

    def generate(self, page_context: PageContext, seo_data: StandardizedSEOData, override: Optional[SEOOverride]) -> List[str]:
        """Orchestre la génération de tous les JSON-LD pertinents."""
        scripts: List[str] = []
        page_type: str = page_context.page_type
        ld_keys_to_generate: List[str] = JSONLD_FOR_PAGE_TYPE.get(page_type, []) # Default: liste vide

        # --- Priorité 1: Override Personnalisé ---
        if override and override.custom_json_ld:
            custom_ld = override.custom_json_ld
            try:
                if isinstance(custom_ld, list): # Si c'est une liste d'objets
                    for ld_item in custom_ld:
                        if isinstance(ld_item, dict): # S'assurer que chaque item est un dict
                            scripts.append(json.dumps(ld_item, ensure_ascii=False, indent=2))
                elif isinstance(custom_ld, dict): # Si c'est un objet unique
                     scripts.append(json.dumps(custom_ld, ensure_ascii=False, indent=2))
                else:
                    print(f"WARN: custom_json_ld pour l'override {override.pk} n'est ni une liste ni un dict.")

                # Si un override existe, on n'ajoute PAS les générés automatiquement ?
                # Ou on les ajoute APRES ? Pour l'instant, on suppose que l'override remplace tout.
                if scripts: # Si on a réussi à générer depuis l'override
                    return scripts
                # Si l'override était invalide, on continue avec la génération auto

            except (json.JSONDecodeError, TypeError) as e:
                print(f"ERROR: Erreur lors de la sérialisation du custom_json_ld pour l'override {override.pk}: {e}")
                # Continuer avec la génération automatique comme fallback

        # --- Génération Automatique ---
        generated_data: Dict[str, Dict] = {} # Pour éviter doublons via clés
        for key in ld_keys_to_generate:
            generator_func = JSONLD_GENERATOR_FUNCTIONS.get(key)
            if generator_func:
                try:
                    ld_data = generator_func(page_context, seo_data, override)
                    if ld_data and isinstance(ld_data, dict): # Vérifier que c'est bien un dict
                        generated_data[key] = ld_data # Stocker avec clé unique
                    else:
                         print(f"DEBUG: Générateur '{key}' n'a rien retourné pour page type '{page_type}'.")
                except Exception as e:
                     print(f"ERROR: Échec de l'exécution du générateur JSON-LD '{key}' pour page type '{page_type}': {e}")
                     import traceback
                     traceback.print_exc() # Afficher la trace complète pour le débogage

        # Sérialiser les dictionnaires uniques générés
        for ld_data in generated_data.values():
             try:
                 scripts.append(json.dumps(ld_data, ensure_ascii=False, indent=2))
             except TypeError as e:
                 print(f"ERROR: Échec de la sérialisation JSON pour {ld_data.get('@type', 'Donnée inconnue')}: {e}")

        return scripts
    



