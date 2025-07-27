from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, NotAuthenticated
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.http import Http404 
from dynamic_forms.metadata import DynamicFormMetadata

class DynamicFormView(APIView):
    """
    Vue API générique pour afficher (GET) et traiter (POST/PUT/PATCH)
    des formulaires basés sur des serializers DRF.
    """
    # --- Configuration (à définir par les sous-classes) ---
    serializer_class = None
    model = None
    queryset = None
    permission_classes = [IsAuthenticated] # Défaut raisonnable
    authentication_classes = APIView.settings.DEFAULT_AUTHENTICATION_CLASSES
    metadata_class = DynamicFormMetadata # Utiliser notre classe personnalisée
    instance_lookup_field = 'pk' # Nom du paramètre URL pour la PK
    success_url = "/" # URL de redirection client par défaut
    success_message = "Formulaire soumis avec succès." # Message de succès par défaut
    perform_action_method_name = None # Pour logique métier personnalisée post-validation

    # --- Initialisation et Vérifications ---
    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     if not self.serializer_class:
    #         raise ImproperlyConfigured(
    #             f"{self.__class__.__name__} manque l'attribut 'serializer_class'."
    #         )

    # --- Méthodes DRF standard ou surchargées ---
    def get_serializer_class(self):
        if not self.serializer_class:
             raise ImproperlyConfigured(f"{self.__class__.__name__} manque 'serializer_class'.")
        return self.serializer_class

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset.all()
        if self.model is not None:
            return self.model._default_manager.all()
        return None

    def get_object(self):
        """
        Récupère l'instance si `instance_lookup_field` est dans l'URL kwargs.
        Retourne None si le lookup kwarg est absent (ex: vue de création).
        Applique les permissions d'objet si un objet est trouvé.
        Lève NotFound si le kwarg est présent mais l'objet n'existe pas.
        Lève PermissionDenied si les permissions d'objet échouent.
        """
        queryset = self.get_queryset()
        lookup_url_kwarg = self.instance_lookup_field

        # CORRECTION : Si le kwarg n'est pas dans l'URL, pas d'objet spécifique visé.
        if lookup_url_kwarg not in self.kwargs:
             return None

        # Si le kwarg EST présent, on DOIT pouvoir chercher l'objet
        filter_kwargs = {self.instance_lookup_field: self.kwargs[lookup_url_kwarg]}
        if queryset is None:
             # Erreur de configuration si on a un lookup kwarg mais pas de queryset/modèle
             raise ImproperlyConfigured(
                 f"{self.__class__.__name__} needs either a 'queryset' or 'model' "
                 f"attribute to use get_object() when '{lookup_url_kwarg}' is in the URL."
             )

        try:
            # Récupérer l'objet ou lever Http404 (qui deviendra NotFound pour l'API)
            obj = get_object_or_404(queryset, **filter_kwargs)
        except Http404:
            raise NotFound("Instance non trouvée.") # Exception API standard
        except Exception as e:
             print(f"Error during get_object lookup in {self.__class__.__name__}: {e}") # Log
             raise NotFound("Erreur lors de la récupération de l'instance.") # Masquer les détails

        # Vérifier les permissions sur l'objet trouvé
        # Ceci lèvera PermissionDenied si l'accès n'est pas autorisé
        self.check_object_permissions(self.request, obj)

        return obj # Retourner l'objet si trouvé et autorisé

    def get_serializer_context(self):
        return {'request': self.request, 'view': self}

    def get_serializer(self, *args, **kwargs):
        """
        Instancie le serializer. Gère l'injection de `instance`, `data`, `context`, `partial`.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())

        instance = None
        lookup_url_kwarg = self.instance_lookup_field

        # Tenter de récupérer l'instance si lookup_kwarg est présent et méthode != POST
        if lookup_url_kwarg in self.kwargs and self.request.method != 'POST':
             try:
                  # get_object gère maintenant le cas où kwarg est absent (retourne None)
                  # et lève les exceptions appropriées si kwarg est présent mais objet non trouvé/permis
                  instance = self.get_object()
             except (NotFound, PermissionDenied, NotAuthenticated) as e:
                  # Si l'objet n'est pas trouvé ou accessible pour GET/PUT/PATCH, lever l'erreur
                  print(f"get_serializer: Cannot retrieve object for detail view/update: {e}")
                  raise e # Relancer l'exception interceptée par DRF

        # Passer l'instance (ou None) au serializer
        if instance:
            kwargs['instance'] = instance

        # Ajouter les données soumises pour POST/PUT/PATCH
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            kwargs['data'] = self.request.data
            # Activer la mise à jour partielle pour PATCH
            if self.request.method == 'PATCH':
                kwargs['partial'] = True

        # Instancier et retourner le serializer
        return serializer_class(*args, **kwargs)

    # --- Gestionnaires de Méthodes HTTP ---
    def get(self, request, *args, **kwargs):

        """ Retourne les métadonnées du formulaire via la classe metadata_class. """
        try:
            metadata = self.metadata_class().determine_metadata(request, self)
            return Response(metadata)
        except Exception as e:
            # Capturer les erreurs potentielles pendant la génération des métadonnées
            print(f"Error generating metadata in GET {self.__class__.__name__}: {e}")
            return Response(
                {"error": "Erreur lors de la génération de la structure du formulaire."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, *args, **kwargs):
        """ Gère la soumission pour création (POST). """
        return self._handle_submission(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """ Gère la soumission pour mise à jour complète (PUT). """
        return self._handle_submission(request, partial=False, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """ Gère la soumission pour mise à jour partielle (PATCH). """
        return self._handle_submission(request, partial=True, *args, **kwargs)

    # --- Logique de Soumission et Action ---
    def _handle_submission(self, request, partial=False, *args, **kwargs):
        """ Logique commune pour traiter les soumissions POST/PUT/PATCH. """
        # Note : 'partial' est passé à get_serializer implicitement via la méthode (PATCH)
        serializer = self.get_serializer() # Obtient le serializer (avec instance/data si applicable)

        if serializer.is_valid():
            # --- SUCCÈS DE LA VALIDATION ---
            try:
                # Exécuter l'action principale (souvent serializer.save() ou méthode perso)
                result_data = self.perform_action(serializer, request, *args, **kwargs)

                # Construire la réponse de succès
                response_data = {
                    "message": self.success_message,
                    "success": True,
                    "redirect_url": self.get_success_url(serializer),
                    "data": result_data # Données retournées par perform_action (ex: PK)
                }
                status_code = status.HTTP_201_CREATED if request.method == 'POST' else status.HTTP_200_OK
                return Response(response_data, status=status_code)

            except Exception as e:
                 # Gérer les erreurs DANS perform_action (ex: erreur base de données, logique métier)
                 print(f"ERROR during perform_action in {self.__class__.__name__}: {e}") # Log important
                 return Response(
                    {"error": "Une erreur interne est survenue lors du traitement de votre demande.", "success": False},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                 )
        else:
             # --- ÉCHEC DE LA VALIDATION ---
             print(f"Validation errors in {self.__class__.__name__}: {serializer.errors}") # Log

             # Générer la structure de base du formulaire pour la réponse
             # (afin que le frontend puisse afficher le formulaire avec les erreurs)
             try:
                metadata_response = self.metadata_class().determine_metadata(request, self)
             except Exception as e:
                 # Si même la génération de métadonnées échoue ici, renvoyer juste les erreurs
                 print(f"Error generating metadata during FAILED submission in {self.__class__.__name__}: {e}")
                 metadata_response = {} # Partir d'un dict vide

             # Ajouter les informations d'échec et les erreurs de validation
             metadata_response['success'] = False
             metadata_response['message'] = "Le formulaire contient des erreurs. Veuillez corriger les champs indiqués."
             # CORRECTION : Ajouter la clé 'errors' contenant TOUTES les erreurs
             metadata_response['errors'] = serializer.errors

             return Response(metadata_response, status=status.HTTP_400_BAD_REQUEST)

    def perform_action(self, serializer, request, *args, **kwargs):
        """
        Action à exécuter après validation réussie.
        Surcharger ou utiliser `perform_action_method_name`.
        Par défaut, tente `serializer.save()`.
        """
        # 1. Méthode spécifique définie sur la vue ?
        if self.perform_action_method_name:
            method_to_call = getattr(self, self.perform_action_method_name, None)
            if method_to_call and callable(method_to_call):
                 return method_to_call(serializer, request, *args, **kwargs)
            else:
                 raise ImproperlyConfigured(
                     f"L'attribut 'perform_action_method_name' pointe vers une méthode "
                     f"'{self.perform_action_method_name}' inexistante ou non appelable "
                     f"sur {self.__class__.__name__}."
                 )

        # 2. Action par défaut : appeler serializer.save() si possible
        if self.model is not None and hasattr(serializer, 'save') and callable(serializer.save):
            try:
                # save() appelle serializer.create() ou serializer.update()
                instance = serializer.save()
                # Retourner la PK est souvent utile
                if hasattr(instance, 'pk'):
                   return {"instance_pk": instance.pk}
                else:
                   # Fallback si pas de PK
                   return serializer.validated_data
            except Exception as e:
                # Capturer les erreurs potentielles de create/update (ex: contraintes DB)
                print(f"Error DURING serializer.save() in {self.__class__.__name__}.perform_action: {e}")
                # Relancer pour que _handle_submission retourne une erreur 500 ou 400 appropriée
                raise e

        # 3. Fallback ultime : si aucune action n'a été effectuée
        print(f"Warning: No specific action performed for {self.__class__.__name__}. Returning validated data.")
        return serializer.validated_data

    def get_success_url(self, serializer):
         """ Retourne l'URL de redirection client après succès. """
         # Peut être surchargée pour dépendre de l'instance/données
         return self.success_url