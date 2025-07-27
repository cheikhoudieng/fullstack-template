# Dynamic Forms Backend (Application Django : `dynamic_forms`)

## Introduction

Cette application Django fournit un système backend robuste et extensible pour générer dynamiquement des structures de formulaires via une API REST et gérer la soumission de ces formulaires. L'objectif est de permettre au frontend de construire des formulaires sans connaître leur structure à l'avance, en se basant sur les métadonnées fournies par l'API.

L'approche est principalement "serializer-driven", utilisant les `Serializers` de Django REST Framework (DRF) comme source de vérité pour la définition des champs, la validation et la logique de traitement des données.

## Fonctionnalités Clés

- **Génération de Métadonnées de Formulaire** : Fournit des endpoints API (`GET`) qui retournent une description JSON détaillée de la structure du formulaire (champs, types, labels, validations de base, options, etc.) via la classe `DynamicFormMetadata`.
- **Gestion Générique des Soumissions** : La vue de base `DynamicFormView` gère les requêtes `POST`, `PUT`, `PATCH` pour la validation et le traitement des soumissions de formulaires.
- **Basé sur les Serializers DRF** : Utilise la puissance des serializers DRF pour la définition des champs, la validation robuste et la sérialisation/désérialisation des données. Supporte à la fois `serializers.Serializer` et `serializers.ModelSerializer`.
- **Extensibilité** : Facile à étendre en ajoutant de nouveaux serializers et en configurant de nouvelles vues héritant de `DynamicFormView`. Permet de définir des logiques spécifiques post-validation via la surcharge de `perform_action`.
- **Intégration DRF Standard** : Utilise les mécanismes standards de DRF pour l'authentification, les permissions et la gestion des réponses/exceptions.

## Concepts Fondamentaux

1.  **Serializers (`serializers.py`)** : Chaque formulaire est défini par une classe héritant de `serializers.Serializer` ou `serializers.ModelSerializer`. Ils définissent :

    - Les champs attendus et leurs types (`CharField`, `EmailField`, `ChoiceField`, etc.).
    - Les règles de validation (requis, longueur max, validateurs spécifiques comme `UniqueValidator`, méthodes `validate_<field>`, méthode `validate`).
    - Pour les serializers _non_-`ModelSerializer` (comme `UserCreateSerializer` dans notre cas pour contourner des problèmes d'introspection), les méthodes `create(self, validated_data)` et/ou `update(self, instance, validated_data)` **doivent** être implémentées pour gérer la logique de sauvegarde en base de données.

2.  **Vue Générique (`views.DynamicFormView`)** : Une classe de vue `APIView` réutilisable qui :

    - Utilise `metadata_class = DynamicFormMetadata` pour les requêtes `GET`, afin de générer la description JSON du formulaire basé sur le serializer associé.
    - Gère les méthodes `POST`/`PUT`/`PATCH` via `_handle_submission`.
    - Appelle `serializer.is_valid()` pour la validation.
    - Appelle `perform_action(serializer, ...)` après validation réussie.
    - Est configurée principalement en définissant l'attribut `serializer_class` dans les vues qui en héritent.
    - Peut optionnellement utiliser le mapping `FORM_SERIALIZERS` et le `form_key` pour des configurations plus dynamiques via l'URL (moins courant si des vues dédiées sont créées).

3.  **Métadonnées (`views.DynamicFormMetadata`)** : Une classe qui surcharge `SimpleMetadata` de DRF pour :

    - Inspecter les `fields` du serializer associé à la vue.
    - Générer une structure JSON détaillée pour chaque champ, incluant `name`, `label`, `type` (logique), `widget` (rendu), `required`, `help_text`, `choices`, `initial`, `value` (si instance), etc.
    - Cette structure est directement consommable par le frontend pour construire l'interface utilisateur.

4.  **Traitement Post-Validation (`views.DynamicFormView.perform_action`)** : Hook principal pour exécuter la logique métier après validation :

    - Par défaut, il tente d'appeler `serializer.save()`. Ceci fonctionne si le serializer est un `ModelSerializer` ou un `Serializer` simple qui implémente `create`/`update`.
    - Peut être surchargé dans les vues filles pour des actions spécifiques (ex: envoyer un email pour un formulaire de contact).
    - Peut être dirigé vers une méthode spécifique de la vue via l'attribut `perform_action_method_name`.

5.  **URLs (`urls.py`)** : Définit comment les URLs mappent vers les vues :
    - Peut avoir des URLs spécifiques pour chaque formulaire (ex: `/api/v1/users/create/` -> `UserCreateView`). C'est l'approche recommandée pour la clarté.
    - Peut avoir une URL générique (ex: `/api/v1/form/<str:form_key>/`) qui utilise le `form_key` et `FORM_SERIALIZERS` pour trouver le bon serializer (moins utilisé maintenant que nous privilégions `serializer_class` sur la vue).

## Configuration et Installation

1.  **Ajouter l'application** : Assurez-vous que `dynamic_forms` et `rest_framework` sont listés dans `INSTALLED_APPS` dans votre `settings.py`.
    ```python
    # settings.py
    INSTALLED_APPS = [
        # ... autres apps
        'rest_framework',
        'rest_framework.authtoken', # Si TokenAuthentication est utilisé
        'dynamic_forms',
        # ...
    ]
    ```
2.  **Dépendances** : Assurez-vous que Django REST Framework est installé :
    ```bash
    pip install djangorestframework
    ```
3.  **URLs Principales** : Incluez les URLs de `dynamic_forms` dans votre `urls.py` principal :

    ```python
    # project/urls.py
    from django.urls import path, include

    urlpatterns = [
        # ... admin, autres urls ...
        path('api/v1/', include('dynamic_forms.urls', namespace='dynamic_forms')),
        # Ou un autre préfixe si désiré
    ]
    ```

## Utilisation : Ajouter un Nouveau Formulaire Dynamique

Pour ajouter la gestion d'un nouveau formulaire (par exemple, un formulaire de feedback) :

1.  **Créer le Serializer** (`dynamic_forms/serializers.py`) :

    - Définissez une nouvelle classe (ex: `FeedbackSerializer`) héritant de `serializers.Serializer` (ou `ModelSerializer` si applicable et sans problème).
    - Listez tous les champs (`subject = serializers.CharField(...)`, `message = serializers.CharField(style={'base_template': 'textarea.html'})`, `rating = serializers.ChoiceField(...)`, etc.).
    - Ajoutez les validateurs nécessaires (`UniqueValidator`, méthodes `validate`, etc.).
    - **Important** : Si vous héritez de `serializers.Serializer`, implémentez `create` et/ou `update` si une action de sauvegarde est nécessaire.

    ```python
    # Exemple simple pour FeedbackSerializer
    class FeedbackSerializer(serializers.Serializer):
        subject = serializers.CharField(max_length=100)
        message = serializers.CharField(style={'base_template': 'textarea.html'})
        rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
        email = serializers.EmailField(required=False)

        # Pas de méthode create ici si on veut juste traiter les données dans la vue
    ```

2.  **Créer la Vue** (`dynamic_forms/views.py`) :

    - Créez une nouvelle classe héritant de `DynamicFormView`.
    - Définissez `serializer_class` pour pointer vers votre nouveau serializer.
    - Définissez `permission_classes`, `authentication_classes` selon les besoins.
    - Définissez `success_url`.
    - **Optionnel (mais courant si pas de `create`/`update` dans le serializer)** : Surchargez `perform_action` (ou utilisez `perform_action_method_name`) pour définir ce qu'il faut faire avec les données validées (ex: envoyer un email).

    ```python
    # Exemple pour FeedbackView
    from .serializers import FeedbackSerializer

    class FeedbackView(DynamicFormView):
        serializer_class = FeedbackSerializer
        permission_classes = [] # Ouvert à tous par exemple
        authentication_classes = []
        success_url = '/feedback/merci/' # URL de redirection après succès

        def perform_action(self, serializer, request, *args, **kwargs):
            # Logique personnalisée pour traiter le feedback
            print("Feedback reçu:", serializer.validated_data)
            # Ici : Envoyer un email, enregistrer quelque part, etc.
            # Simuler une action réussie
            return {"status": "Feedback enregistré (simulation)"}
    ```

3.  **Définir l'URL** (`dynamic_forms/urls.py`) :

    - Ajoutez un `path` qui mappe une URL vers votre nouvelle vue.

    ```python
    # urls.py
    from django.urls import path
    from . import views

    app_name = 'dynamic_forms'

    urlpatterns = [
        # ... autres urls (UserCreateView, ContactFormView...)
        path('feedback/', views.FeedbackView.as_view(), name='feedback_form'),
    ]
    ```

Le frontend peut maintenant faire un `GET` sur `/api/v1/feedback/` pour obtenir la structure du formulaire de feedback et un `POST` sur la même URL pour le soumettre.

## Personnalisation

- **Serializers** : C'est le point principal pour définir la structure et la validation.
- **`perform_action` / `perform_action_method_name`** : Pour la logique métier spécifique après validation.
- **`get_success_url`** : Pour une logique de redirection plus dynamique.
- **Permissions/Authentification** : À définir sur chaque vue héritant de `DynamicFormView`.
- **`DynamicFormMetadata`** : Peut être étendue pour ajouter plus d'informations dans la description JSON (ex: attributs `data-*`, configurations de widgets spécifiques).
