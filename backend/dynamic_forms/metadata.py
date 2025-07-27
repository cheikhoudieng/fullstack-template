# Fichier: backend/dynamic_forms/metadata.py (ou où vous préférez le placer)

from rest_framework.metadata import SimpleMetadata
from rest_framework import serializers
from django.utils.encoding import smart_str # Pour l'encodage correct des noms d'affichage

class DynamicFormMetadata(SimpleMetadata):
    """
    Métadonnées améliorées pour DynamicFormView.

    Fonctionnalités :
    - Extrait les informations essentielles de chaque champ du serializer (type, label, aide, etc.).
    - Détermine la valeur initiale (pour la création) ou actuelle (pour la mise à jour) du champ.
    - Fournit les options (choices) pour les champs de type sélection (ChoiceField, RelatedField).
    - Distingue les types de widgets (select, select_multiple, textarea, etc.).
    - N'inclut PAS les erreurs de validation (celles-ci sont ajoutées à la réponse
      lors d'une soumission invalide par la vue DynamicFormView).
    """

    def determine_metadata(self, request, view):
        """
        Génère la structure de métadonnées pour la vue donnée et la requête actuelle.
        """
        # Utilise la méthode parente pour obtenir les métadonnées DRF de base (peut inclure 'actions')
        metadata = super().determine_metadata(request, view)
        # Récupère une instance du serializer configuré sur la vue.
        # get_serializer() gère l'injection de `instance` si une PK est dans l'URL (pour GET/PUT/PATCH)
        # et de `data` si méthode = POST/PUT/PATCH.
        metadata['description'] = "" # important
        serializer = view.get_serializer()

        # Informations générales sur la vue/formulaire
        metadata['view_name'] = view.get_view_name()
        # metadata['view_description'] = "" #view.get_view_description(html=False) 
        metadata['success_url'] = getattr(view, 'success_url', None)
        metadata['success_message'] = getattr(view, 'success_message', "Formulaire soumis avec succès.")

        detailed_fields = []
        # Récupère l'instance du modèle si elle a été passée au serializer (pour pré-remplissage lors de GET/PUT/PATCH)
        instance = getattr(serializer, 'instance', None)

        # Itérer sur tous les champs définis dans le serializer
        for name, field in serializer.fields.items():
            # Exclure les champs en lecture seule des métadonnées pour les soumissions (POST/PUT/PATCH),
            # mais les inclure pour l'affichage (GET)
            if field.read_only and request.method != 'GET':
                 continue

            # --- Détermination des types (logique + widget) ---
            logical_type = self._get_field_type(field)
            widget_type = self._get_widget_type(field, logical_type)

            # --- Informations de base du champ ---
            field_data = {
                "name": name,
                "type": logical_type, # Type de données logique (text, number, select...)
                "widget": widget_type, # Type de contrôle HTML suggéré (textarea, password, select_multiple...)
                "required": field.required,
                "read_only": field.read_only,
                "label": smart_str(field.label) if field.label else name.replace('_', ' ').title(),
                "help_text": smart_str(field.help_text) if field.help_text else "",
                "max_length": getattr(field, 'max_length', None),
                "min_length": getattr(field, 'min_length', None),
                "choices": None, # Rempli ci-dessous si applicable
                "value": None,   # Rempli ci-dessous
                # Les erreurs ne sont PAS incluses ici. Elles sont ajoutées dans la réponse
                # de _handle_submission en cas d'échec de validation.
            }

            # --- Déterminer la valeur du champ (pour pré-remplissage GET) ---
            field_value = None
            # 1. Priorité : Valeur actuelle de l'instance (si on modifie un objet existant)
            if instance:
                try:
                    source_attr = field.source or name # Nom de l'attribut sur le modèle
                    current_value = instance
                    # Gérer les accès potentiellement imbriqués (ex: 'profile.user.email')
                    for part in source_attr.split('.'):
                        if current_value is None: break # Arrêter si un maillon est None
                        attr = getattr(current_value, part, None) # Récupérer l'attribut/relation

                        # Vérifier si c'est un Manager (relation ToMany ou inverse)
                        if callable(getattr(attr, 'all', None)):
                            # Si oui, obtenir la liste des PKs des objets liés
                            current_value = list(attr.values_list('pk', flat=True))
                            # C'est la valeur finale pour ce champ (liste de PKs)
                            break
                        else:
                             # Sinon, continuer la descente dans les attributs imbriqués
                             current_value = attr

                    field_value = current_value

                    # Post-traitement pour les relations ToOne (ForeignKey)
                    # Si c'est un PrimaryKeyRelatedField simple (pas dans un ListSerializer)
                    # et que la valeur est un objet modèle (pas une PK), extraire la PK.
                    if isinstance(field, serializers.PrimaryKeyRelatedField) and hasattr(field_value, 'pk'):
                         # (La condition not field.many a été retirée car non fiable)
                         # Le cas M2M a déjà été traité par .all() plus haut.
                         # Donc ici, c'est forcément une FK simple.
                         field_value = field_value.pk

                except AttributeError:
                    # Si un attribut n'est pas trouvé lors de la recherche imbriquée
                    field_value = None

            # 2. Sinon (pas d'instance ou valeur non trouvée sur l'instance) :
            #    Utiliser la valeur initiale/défaut définie sur le champ serializer
            if field_value is None:
                # get_initial() gère 'initial=' et 'default=' définis sur le champ
                field_value = field.get_initial()

            # 3. Cas spécifique pour les booléens (checkboxes) :
            #    Si aucune valeur n'est définie, considérer comme False
            if field_data['type'] == 'checkbox' and field_value is None:
                field_value = False

            # Assigner la valeur déterminée
            field_data['value'] = field_value

            # --- Déterminer les Choix (Choices) pour les listes déroulantes etc. ---
            choices = []
            # Déterminer sur quel champ chercher les choix (le champ lui-même ou son enfant si c'est un ListSerializer)
            actual_field_for_choices = field.child if isinstance(field, serializers.ListSerializer) else field

            # A. Si le champ (ou son enfant) a un attribut 'choices' (ChoiceField)
            if hasattr(actual_field_for_choices, 'choices') and actual_field_for_choices.choices:
                choices = [
                    {"value": key, "display_name": smart_str(value)}
                    for key, value in actual_field_for_choices.choices.items() # DRF utilise {val: display}
                ]
            # B. Si le champ (ou son enfant) est un champ de relation (RelatedField)
            elif isinstance(actual_field_for_choices, serializers.RelatedField):
                try:
                    # Récupérer le queryset associé au champ de relation
                    queryset = actual_field_for_choices.get_queryset()
                    # Attention : Performance critique pour les grands querysets !
                    # Envisager une limite et/ou une API de recherche/autocomplete pour le frontend.
                    limit = 200 # Limite arbitraire pour éviter de charger trop d'options
                    choices = [
                        {"value": obj.pk, "display_name": smart_str(obj)}
                        for obj in queryset[:limit] # Appliquer la limite
                    ]
                    # Optionnel : Indiquer si la liste a été tronquée
                    if queryset.count() > limit:
                         choices.append({"value": None, "display_name": f"... ({queryset.count() - limit} autres)", "disabled": True})
                except Exception as e:
                    # Logguer l'erreur si la récupération du queryset échoue
                    print(f"Warning: Could not retrieve choices for related field '{name}': {e}")
                    choices = [] # Fournir une liste vide en cas d'échec

            # Assigner les choix s'il y en a
            if choices:
                field_data['choices'] = choices

            # Ajouter les données complètes du champ à la liste
            detailed_fields.append(field_data)

        # --- Structure finale de la réponse de métadonnées ---
        # Pour une requête GET, on fournit principalement la liste des champs
        if request.method == 'GET':
             metadata['fields'] = detailed_fields
             # Supprimer la clé 'actions' générée par SimpleMetadata si elle existe,
             # car elle est moins pertinente pour une simple structure de formulaire GET.
             metadata.pop('actions', None)
        else:
             # Si cette classe est utilisée pour d'autres méthodes (ex: OPTIONS),
             # on essaie de respecter la structure 'actions' de DRF.
             if 'actions' not in metadata: metadata['actions'] = {}
             method_key = request.method.upper() # Ex: 'POST'
             if method_key not in metadata['actions']: metadata['actions'][method_key] = {}
             # Ajouter les champs détaillés sous l'action correspondante
             metadata['actions'][method_key]['fields'] = detailed_fields
             # Ajouter l'URL de soumission (utile si différent de l'URL GET)
             metadata['actions'][method_key]['url'] = request.build_absolute_uri()

        return metadata

    # --- Méthodes utilitaires pour déterminer les types (logique et widget) ---

    def _get_field_type(self, field):
        """Détermine le type de données logique du champ."""
        # Vérifier ListSerializer en premier pour gérer le cas many=True
        if isinstance(field, serializers.ListSerializer):
            child_field = field.child
            # Cas spécifique M2M via PrimaryKeyRelatedField
            if isinstance(child_field, serializers.PrimaryKeyRelatedField):
                return 'select_related_multiple'
            # Cas spécifique MultipleChoiceField (moins courant avec ListSerializer mais possible)
            if isinstance(child_field, serializers.ChoiceField):
                 return 'select_multiple'
            # Fallback pour d'autres types d'enfants dans un ListSerializer (rare pour les formulaires)
            # On pourrait retourner 'list' ou le type de l'enfant si pertinent.
            return 'list' # Type générique pour une liste

        # Vérifier les types de champs spécifiques (ordre important)
        if isinstance(field, serializers.EmailField): return 'email'
        if isinstance(field, serializers.URLField): return 'url'
        if isinstance(field, serializers.IntegerField): return 'number'
        if isinstance(field, (serializers.DecimalField, serializers.FloatField)): return 'number'
        if isinstance(field, serializers.DateField): return 'date'
        if isinstance(field, serializers.DateTimeField): return 'datetime-local'
        if isinstance(field, serializers.TimeField): return 'time'
        if isinstance(field, serializers.BooleanField): return 'checkbox'
        # Champs de sélection simple (ForeignKey ou ChoiceField simple)
        if isinstance(field, serializers.PrimaryKeyRelatedField): return 'select_related'
        if isinstance(field, serializers.ChoiceField): return 'select'
        # Fichiers
        if isinstance(field, serializers.ImageField): return 'image' # Spécifique avant FileField
        if isinstance(field, serializers.FileField): return 'file'
        # Champs texte, vérifier si c'est un Textarea
        if isinstance(field, serializers.CharField):
            # Détection de Textarea basée sur le style (plus fiable)
            if getattr(field, 'style', {}).get('base_template') == 'textarea.html':
                return 'textarea'
            # Sinon, c'est un champ texte simple
            return 'text'
        # Autres types possibles : JSONField, UUIDField, etc. à ajouter si nécessaire

        # Type par défaut si non reconnu
        return 'text'

    def _get_widget_type(self, field, logical_type):
        """Détermine le type de widget HTML suggéré, basé sur le type logique et le style."""
        # Vérifier d'abord les styles spécifiques qui forcent un widget
        style = getattr(field, 'style', {})
        if style.get('input_type') == 'password':
            return 'password'
        # Si le type logique est déjà 'textarea', le widget est 'textarea'
        if logical_type == 'textarea':
            return 'textarea'

        # Mapper les types logiques aux widgets courants
        widget_map = {
            'email': 'email',
            'url': 'url',
            'number': 'number',
            'date': 'date',
            'datetime-local': 'datetime-local',
            'time': 'time',
            'checkbox': 'checkbox',
            'select': 'select',
            'select_multiple': 'select_multiple', # Nécessite l'attribut 'multiple' en HTML
            'select_related': 'select',
            'select_related_multiple': 'select_multiple', # Nécessite 'multiple' en HTML
            'file': 'file',
            'image': 'file', # Souvent un input type="file" avec accept="image/*"
            'text': 'text',
            'list': 'list' # Pas de widget HTML standard, dépend de l'implémentation frontend
        }
        # Retourner le widget mappé, ou le type logique par défaut si non trouvé
        return widget_map.get(logical_type, logical_type)