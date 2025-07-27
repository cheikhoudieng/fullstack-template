# Cicaw Marketplace - Système de Gestion SEO (Backend Django)

## 1. Introduction

Ce document décrit le système de gestion SEO implémenté dans le backend Django de Cicaw. L'objectif principal est d'assurer un référencement optimal pour une application web de type Single Page Application (SPA) construite avec React, en servant les métadonnées SEO essentielles (balises Meta, Open Graph, Twitter Cards, JSON-LD) directement dans le rendu HTML initial côté serveur (Server-Side Rendering - SSR).

Cela garantit que les robots des moteurs de recherche (Google, Bing, etc.) et les plateformes sociales (Facebook, Twitter, etc.) reçoivent les informations contextuelles nécessaires pour comprendre et indexer correctement chaque page de la marketplace Cicaw (page d'accueil, produits, catégories, vendeurs, etc.), même avant l'exécution du JavaScript côté client par React.

## 2. Fonctionnalités Clés

- **Rendu Côté Serveur (SSR)** des balises SEO essentielles (`<title>`, `<meta>`, `<link rel="canonical">`).
- **Génération Dynamique** des métadonnées basée sur le contexte de la page actuelle (produit, catégorie, page statique, etc.).
- **Support Complet des Données Structurées (JSON-LD)** pour différents types de Schémas (WebSite, Organization, Product, BreadcrumbList, etc.) afin d'améliorer la compréhension par les moteurs de recherche et potentiellement obtenir des Rich Results.
- **Gestion des Protocoles Sociaux** Open Graph (og:_) et Twitter Cards (twitter:_) pour un partage optimisé sur les réseaux.
- **Configuration Globale Centralisée** pour les valeurs par défaut (titre, description, images, etc.).
- **Système de Surcharge (Override)** via l'interface d'administration Django, permettant de modifier manuellement les métadonnées pour des pages spécifiques (par objet ou par URL).
- **Architecture Modulaire et Extensible** facilitant l'ajout de support SEO pour de nouveaux types de pages ou de nouvelles métadonnées.

## 3. Architecture Générale

Le système suit un flux de traitement clair pour chaque requête nécessitant un rendu HTML initial avec SEO :

1.  **Requête Entrante**: Une requête HTTP arrive sur une URL Django gérée par une vue héritant de `BasePageView`.
2.  **Identification du Contexte (Vue)**: La vue détermine le `page_type` (ex: 'product', 'home'), récupère l'objet principal (ex: instance de `Product`) via `get_object()` et les données additionnelles (ex: breadcrumbs) via `get_extra_seo_data()`. Elle assemble ces informations dans un objet `PageContext`.
3.  **Orchestration (SEOOrchestrator)**: La vue passe le `PageContext` au service `SEOOrchestrator`.
4.  **Récupération des Données Brutes (SEODataProvider)**: L'orchestrateur sélectionne le `SEODataProvider` approprié basé sur le `page_type`. Le provider interroge la base de données (si nécessaire) et normalise les informations pertinentes (titre, description, image, prix, etc.) dans un objet `StandardizedSEOData`.
5.  **Recherche de Surcharge (OverrideService)**: L'orchestrateur demande à `OverrideService` s'il existe un `SEOOverride` actif pour l'objet ou le chemin d'URL du `PageContext`.
6.  **Génération des Métadonnées (Generators)**: L'orchestrateur passe `PageContext`, `StandardizedSEOData` et l'`SEOOverride` (s'il existe) aux différents générateurs spécialisés :
    - `MetaTagGenerator`: Génère `title`, `meta description`, `canonical URL`, `meta robots`.
    - `SocialTagGenerator`: Génère les balises `og:*` et `twitter:*`.
    - `JsonLdProcessor`: Génère les scripts `<script type="application/ld+json">` pertinents pour le `page_type`.
7.  **Assemblage du Contexte Final**: L'orchestrateur collecte les résultats des générateurs et les structure dans un dictionnaire `seo` unique (`{'title': ..., 'canonical': ..., 'meta_tags': [...], 'json_ld': [...]}`).
8.  **Rendu du Template**: La vue passe ce dictionnaire `seo` (avec d'autres données si nécessaire) au template Django (`build/index.html`).
9.  **HTML Final**: Le template Django utilise les variables du dictionnaire `seo` pour générer les balises HTML correspondantes dans la section `<head>` de la page servie au navigateur.

## 4. Composants Détaillés

L'ensemble de la logique SEO est principalement contenu dans l'application Django `seo`.

### 4.1. Configuration (`settings.py` & `seo/config.py`)

- **`settings.SEO_SETTINGS` (dict)**: Défini dans le fichier `settings.py` principal de Django. Contient toutes les valeurs par défaut globales et la configuration de base (titres, descriptions, images par défaut, nom du site, handle Twitter, devise, locale, données d'organisation pour JSON-LD, etc.). **Il est crucial de personnaliser ces valeurs.**
- **`seo/config.py (SEOConfig)`**: Une classe simple fournissant une interface pratique (via des propriétés) pour accéder aux valeurs de `settings.SEO_SETTINGS` avec des valeurs par défaut intégrées si une clé manque. Une instance `seo_config` est disponible pour usage interne dans l'application `seo`.

### 4.2. Modèles (`seo/models.py`)

- **`SEOOverride`**: Le modèle clé permettant de surcharger manuellement les métadonnées générées.
  - **Ciblage**: Peut cibler soit un objet spécifique via `ContentType` et `object_id` (GenericForeignKey), soit un chemin d'URL exact via le champ `path`. Une contrainte assure qu'un seul type de ciblage est utilisé.
  - **Champs**: Contient des champs optionnels pour chaque métadonnée surchargeable (title, meta*description, canonical_url, og*_, twitter\__, robots_meta, etc.). Si un champ est laissé vide, la valeur générée dynamiquement (ou la valeur par défaut) sera utilisée.
  - **Statut**: Un champ `is_active` permet d'activer/désactiver facilement une surcharge.
- **`TimestampedModel`**: Modèle abstrait ajoutant `added_date` et `last_update`.

### 4.3. Structures de Données (`seo/data.py`)

- **`PageContext` (dataclass)**: Encapsule le contexte brut d'une requête/vue transmis à l'orchestrateur : `request`, `obj` (l'objet principal), `page_type` (string), `view_kwargs`, `extra_data`.
- **`StandardizedSEOData` (dataclass)**: Représente les données SEO brutes _normalisées_ extraites par un `SEODataProvider`. Contient des champs génériques (name, description, main_image_url, url_path, etc.) et des champs plus spécifiques (price, currency, brand, author_name, etc.) pour différents types de contenu.

### 4.4. Providers (`seo/providers.py`)

- **Rôle**: Extraire les informations pertinentes du `PageContext` (en particulier de `context.obj`) et les transformer en un objet `StandardizedSEOData`. Chaque provider est spécifique à un `page_type`.
- **Exemples**: `ProductSEODataProvider`, `CategorySEODataProvider`, `HomePageSEODataProvider`, etc.
- **`PROVIDER_REGISTRY` (dict)**: Un dictionnaire qui mappe les chaînes `page_type` à l'instance du provider correspondant.
- **`get_provider(page_type)`**: Fonction utilitaire pour récupérer le provider depuis le registre.

### 4.5. Générateurs (`seo/generators/`)

- **Rôle**: Prendre `PageContext`, `StandardizedSEOData`, et l'`SEOOverride` pour produire la sortie SEO finale.
- **`generators/meta.py (MetaTagGenerator)`**: Génère un dictionnaire contenant `title`, `meta_description`, `canonical`, `robots`. Utilise une logique de priorité : Override > Donnée Standardisée > Défaut (`seo_config`). Nécessite `PageContext` pour construire l'URL canonique absolue.
- **`generators/social.py (SocialTagGenerator)`**: Génère un dictionnaire contenant deux listes : `og_tags` et `twitter_tags`. Chaque tag est un dictionnaire `{'type': 'property'/'name', 'name_or_property': 'og:xxx', 'content': '...'}`. Logique de priorité similaire. Nécessite `PageContext` pour l'URL absolue `og:url`.
- **`generators/jsonld.py (JsonLdProcessor)`**: Orchestre la génération des scripts JSON-LD.
  - **`JSONLD_GENERATOR_FUNCTIONS` (dict)**: Mappe une clé de type de schéma (ex: 'product') à la fonction Python qui génère ce JSON-LD.
  - **`JSONLD_FOR_PAGE_TYPE` (dict)**: Mappe un `page_type` à une liste de clés de schémas JSON-LD à générer pour cette page (ex: `'product': ['product', 'breadcrumb', 'website']`).
  - Les fonctions génératrices spécifiques (ex: `generate_product_ld`) reçoivent `PageContext`, `StandardizedSEOData`, `override` et retournent un dictionnaire Python représentant le JSON-LD (ou `None`). `JsonLdProcessor.generate` retourne une liste de chaînes JSON sérialisées prêtes pour le template. Nécessite `PageContext` pour les URLs absolues dans le JSON-LD.

### 4.6. Services (`seo/services.py`)

- **`OverrideService`**: Service simple responsable de trouver le `SEOOverride` actif pertinent pour un `PageContext` donné.
- **`SEOOrchestrator`**: Le chef d'orchestre. Coordonne l'appel au provider, au service d'override, et aux différents générateurs pour assembler le dictionnaire `seo` final passé au template.

### 4.7. Admin (`seo/admin.py`)

- **`SEOOverrideAdmin`**: Configure l'interface d'administration pour le modèle `SEOOverride`.
  - Utilise des `fieldsets` pour organiser le formulaire.
  - Fournit des affichages personnalisés dans la liste (`list_display`) pour la clarté.
  - Inclut un champ en lecture seule (`display_linked_object`) pour aider à vérifier l'objet lié lors du ciblage par ID, même sans `django-admin-genericfk`.

### 4.8. Vues (`BasePageView`)

- **`your_app/views.py (BasePageView)`**: Une classe de vue générique dont toutes les vues de rendu de l'application React devraient hériter.
  - Attribut `page_type`: Doit être défini par les sous-classes (ex: `'product'`).
  - Méthode `get_object()`: Doit être surchargée par les sous-classes pour retourner l'instance du modèle principal (si applicable).
  - Méthode `get_extra_seo_data()`: Peut être surchargée pour fournir des données additionnelles (ex: `{'breadcrumbs': [('Accueil', '/'), ...]}`).
  - Méthode `get()`: Gère le flux principal : création de `PageContext`, appel à `SEOOrchestrator`, rendu du template `build/index.html` avec le contexte `{'seo': seo_context_data}`.

### 4.9. Template (`backend/template/build/index.html`)

- Le template HTML racine qui est servi par Django.
- Il utilise les variables du dictionnaire `seo` pour populer la section `<head>`:
  - `<title>{{ seo.title }}</title>`
  - `<link rel="canonical" href="{{ seo.canonical }}">` (avec condition `{% if seo.canonical %}`)
  - Boucle `{% for tag in seo.meta_tags %}` pour générer les `<meta name="..." ...>` et `<meta property="..." ...>`.
  - Boucle `{% for script_content in seo.json_ld %}` pour générer les `<script type="application/ld+json">`, en utilisant le filtre `{{ script_content|safe }}`.

## 5. Configuration Initiale Essentielle

Avant d'utiliser le système, vous **devez** configurer le dictionnaire `SEO_SETTINGS` dans votre fichier `settings.py`. Voici les clés les plus critiques à définir :

- `DEFAULT_TITLE`
- `TITLE_TEMPLATE`
- `DEFAULT_DESCRIPTION`
- `DEFAULT_OG_IMAGE` (URL Absolue!)
- `SITE_NAME`
- `TWITTER_SITE` (Handle Twitter avec @)
- `DEFAULT_LOCALE` (ex: 'fr_SN')
- `DEFAULT_CURRENCY` (ex: 'XOF')
- `JSONLD_DEFAULT_ORGANIZATION`:
  - `url` (URL page d'accueil absolue)
  - `logo` (URL logo absolue)
  - `sameAs` (Liste des URLs complètes de vos profils sociaux)
  - `contactPoint` (si applicable)
  - `address` (au minimum `addressCountry`)

## 6. Utilisation Quotidienne (Workflow Développeur)

Lorsque vous créez une nouvelle page ou section dans votre application React qui nécessite un rendu initial côté Django avec SEO :

1.  **Créez la Vue Django**: Faites-la hériter de `BasePageView`.
2.  **Définissez `page_type`**: Attribuez une chaîne unique et descriptive (ex: `'vendor_shop'`).
3.  **Implémentez `get_object()`**: Si la page concerne un objet spécifique (Produit, Catégorie, Vendeur...), retournez cette instance ici. Sinon, laissez `return None`.
4.  **Implémentez `get_extra_seo_data()`**: Si nécessaire, retournez des données supplémentaires comme les `breadcrumbs`.
5.  **Vérifiez/Créez le `SEODataProvider`**: Assurez-vous qu'il existe un provider dans `seo/providers.py` pour votre `page_type` et qu'il est enregistré dans `PROVIDER_REGISTRY`. Assurez-vous qu'il retourne un objet `StandardizedSEOData` correctement rempli.
6.  **Vérifiez/Configurez JSON-LD**:
    - Assurez-vous que les fonctions génératrices nécessaires existent dans `seo/generators/jsonld.py` et sont enregistrées dans `JSONLD_GENERATOR_FUNCTIONS`.
    - Ajoutez une entrée pour votre `page_type` dans `JSONLD_FOR_PAGE_TYPE` listant les clés des schémas JSON-LD à inclure.
7.  **Définissez l'URL Django**: Connectez une URL à votre nouvelle vue dans `urls.py`.
8.  **(Optionnel) Testez**: Vérifiez la sortie de `pprint(seo_context_data)` dans la vue et le code source HTML généré.

## 7. Gestion via l'Admin Django

L'interface d'administration Django vous permet de gérer les `SEOOverride`.

- Accédez à la section "SEO" -> "Surcharges SEO".
- **Créer une Surcharge**:
  - Cliquez sur "Ajouter Surcharge SEO".
  - **Ciblage**:
    - _Par Objet_: Sélectionnez le "Type de Contenu" (ex: Product, Category) et entrez l'"ID de l'Objet" (le PK). Laissez "Chemin d'URL" vide.
    - _Par URL_: Laissez "Type de Contenu" et "ID de l'Objet" vides. Entrez le "Chemin d'URL" exact (commençant par `/`, ex: `/connexion/`).
  - **Champs SEO**: Remplissez _uniquement_ les champs que vous souhaitez surcharger. Laissez les autres vides pour utiliser les valeurs dynamiques/par défaut.
  - **Activer**: Assurez-vous que la case "Actif" est cochée.
  - Sauvegardez. Le champ "Objet lié" vous confirmera l'objet ciblé si vous avez utilisé le ciblage par ID.
- **Modifier/Désactiver**: Vous pouvez éditer ou désactiver (décocher "Actif") une surcharge existante.

## 8. Extension du Système

Pour ajouter le support SEO à un nouveau type de contenu (ex: une page profil Vendeur):

1.  **Définir le Type de Page**: Choisissez une chaîne unique, ex: `'vendor_profile'`.
2.  **Créer le Data Provider**: Créez une classe `VendorProfileSEODataProvider(SEODataProvider)` dans `seo/providers.py`. Implémentez `get_seo_data(self, context)` pour extraire les infos du modèle `Vendor` (nom, description, logo, etc.) et retourner un `StandardizedSEOData`.
3.  **Enregistrer le Provider**: Ajoutez `'vendor_profile': VendorProfileSEODataProvider()` à `PROVIDER_REGISTRY`.
4.  **(Si nécessaire) Créer des Fonctions JSON-LD**: Si vous avez besoin de schémas JSON-LD spécifiques (ex: `ProfilePage`, un `LocalBusiness` pour le vendeur), créez les fonctions correspondantes dans `seo/generators/jsonld.py` (ex: `generate_vendor_profile_ld`) et enregistrez-les dans `JSONLD_GENERATOR_FUNCTIONS`.
5.  **Mapper JSON-LD**: Ajoutez `'vendor_profile': ['profile_page', 'breadcrumb', ...]` à `JSONLD_FOR_PAGE_TYPE` dans `seo/generators/jsonld.py`.
6.  **Créer la Vue Django**: Créez `VendorProfileView(BasePageView)`, définissez `page_type = 'vendor_profile'`, implémentez `get_object()` pour récupérer le `Vendor`, etc.

## 9. Troubleshooting / Débogage

- **Métadonnées manquantes ou incorrectes ?**
  1.  **Activez le `pprint`**: Décommentez `pprint.pprint(seo_context_data)` dans `BasePageView.get()` pour voir les données brutes générées. Vérifiez `canonical`, `meta_tags`, `json_ld`.
  2.  **Vérifiez le Provider**: Le bon provider est-il appelé ? Retourne-t-il les bonnes données dans `StandardizedSEOData` (surtout `url_path` pour canonical/urls absolues)?
  3.  **Vérifiez les Générateurs**:
      - La logique dans `MetaTagGenerator`, `SocialTagGenerator` est-elle correcte (priorités, fallbacks) ? Utilisent-ils bien `page_context.request.build_absolute_uri` ?
      - Le `JsonLdProcessor` a-t-il la bonne configuration (`JSONLD_FOR_PAGE_TYPE`, fonctions enregistrées) ? Les fonctions de génération retournent-elles bien des dictionnaires (et non `None` à cause de données manquantes) ?
  4.  **Vérifiez les `settings.SEO_SETTINGS`**: Les valeurs par défaut (images, URLs) sont-elles correctement définies et accessibles ?
  5.  **Vérifiez le Template**: La syntaxe (`{{ seo.title }}`, boucles, filtre `|safe`) est-elle exacte ? Les noms de variables correspondent-ils ?
  6.  **Vérifiez les Overrides**: Y a-t-il un `SEOOverride` actif pour cette page qui écraserait les valeurs avec des champs vides ?
- **Erreur `build_absolute_uri` ?**: Assurez-vous que l'objet `request` est bien passé et utilisé correctement dans les générateurs qui en ont besoin.
- **JSON-LD Invalide ?**: Utilisez l'[Outil de test des résultats enrichis de Google](https://search.google.com/test/rich-results) ou le [Schema Markup Validator](https://validator.schema.org/) pour valider le code JSON-LD généré (copiez-collez depuis le code source de la page).

## 10. Dépendances

Ce système repose principalement sur les fonctionnalités intégrées de Django :

- Django ORM et Modèles
- GenericForeignKey (ContentType framework)
- Système de Templates Django
- Gestion des Vues (Class-Based Views)
- Système de Settings

## 11. Améliorations Possibles

- **Mise en Cache**: Mettre en cache les requêtes `SEOOverride` ou même les résultats de `get_seo_context` pour les pages peu changeantes.
- **Internationalisation (i18n)**: Adapter le système pour gérer plusieurs langues (balises `hreflang`, récupération de contenu traduit).
- **Schémas JSON-LD Avancés**: Implémenter plus de types de schémas (ex: `CollectionPage`, `Offer`, `Review`, `FAQPage`).
- **Intégration Médias Améliorée**: Utiliser `django-imagekit` ou `sorl-thumbnail` pour générer automatiquement les tailles d'images recommandées pour OG/Twitter à partir d'une image source.
- **Interface Utilisateur pour Overrides**: Créer une interface plus conviviale (potentiellement en React dans l'admin) pour gérer les surcharges.
- **Génération Sitemap**: Utiliser `django.contrib.sitemaps` et y intégrer la logique d'URL (potentiellement `get_absolute_url` sur les providers/modèles).
