from rest_framework.permissions import AllowAny, IsAuthenticated
from user_auth.models import User, PasswordResetToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
from dynamic_forms.views import DynamicFormView
from django.middleware.csrf import get_token
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as simple_jwt_settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login 
from rest_framework_simplejwt.exceptions import  TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView
from user_auth.authentication import CookieJWTAuthentication 
from user_auth.serializers import PasswordResetRequestSerializer, UserProfileSerializer, UserCreateSerializer, LoginSerializer, PasswordResetConfirmSerializer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied

UserModel = get_user_model()
send_templated_email = None


class UserCreateView(DynamicFormView):
    model = User
    permission_classes = (AllowAny,)
    authentication_classes = []
    success_url = '/login'
    serializer_class = UserCreateSerializer


class LoginFormView(DynamicFormView):
    permission_classes = (AllowAny,)
    authentication_classes = []
    success_url = '/'
    serializer_class = LoginSerializer
    description = ""


class GetCSRFToken(APIView):
    permission_classes = (AllowAny, )

    def get(self, request, format=None):
        csrf_token = get_token(request)
        return Response({'csrfToken': csrf_token})
    

class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):

        # Utilise UserModel.USERNAME_FIELD pour être flexible (email ou username)
        identifier_field = "identifier"
        identifier = request.data.get(identifier_field)
        password = request.data.get('password')

        if not identifier or not password:
            return Response(
                # Message générique légèrement amélioré
                {'detail': (f'Veuillez fournir {identifier_field} et mot de passe.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Utilise ** pour passer les credentials dynamiquement basé sur identifier_field
        user = authenticate(request, **{"username": identifier, 'password': password})

        # --- CORRECTION : Utiliser simple_jwt_config PARTOUT ---
        simple_jwt_config = settings.SIMPLE_JWT

        if user is not None:
            # --- RECOMMANDATION : Décommenter la vérification is_active ---
            if not user.is_active:
                 return Response({'detail': ('Le compte utilisateur est désactivé.')}, status=status.HTTP_401_UNAUTHORIZED)

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)


            
            user_serializer = UserProfileSerializer(User.objects.get(id=user.id))
            response = Response({
                'user': user_serializer.data,
                'success':True
            }, status=status.HTTP_200_OK)

            # Configuration des cookies depuis les settings SIMPLE_JWT
            # --- CORRECTION : Utiliser simple_jwt_config ici ---
            auth_cookie_name = simple_jwt_config.get('AUTH_COOKIE')
            auth_cookie_refresh_name = simple_jwt_config.get('AUTH_COOKIE_REFRESH') # Utiliser .get()
            auth_cookie_secure = simple_jwt_config.get('AUTH_COOKIE_SECURE')       # Utiliser .get()
            auth_cookie_http_only = simple_jwt_config.get('AUTH_COOKIE_HTTP_ONLY') # Utiliser .get()
            auth_cookie_path = simple_jwt_config.get('AUTH_COOKIE_PATH', '/')      # .get() avec défaut
            auth_cookie_samesite = simple_jwt_config.get('AUTH_COOKIE_SAMESITE')   # Utiliser .get()
            auth_cookie_domain = simple_jwt_config.get('AUTH_COOKIE_DOMAIN')       # Utiliser .get()

            # Vérifier que les clés essentielles existent (optionnel mais plus sûr)
            if not all([auth_cookie_name, auth_cookie_refresh_name, auth_cookie_path, auth_cookie_samesite]):
                 # Gérer l'erreur de configuration - loguer, renvoyer une 500, etc.
                 # Pour l'instant, on peut supposer qu'ils sont définis si on utilise les cookies
                 pass

            # Définir les cookies HttpOnly dans la réponse
            response.set_cookie(
                key=auth_cookie_name,
                value=access_token,
                httponly=auth_cookie_http_only,
                secure=auth_cookie_secure,
                samesite=auth_cookie_samesite,
                path=auth_cookie_path,
                domain=auth_cookie_domain,
                # Pas d'expires/max_age pour en faire un cookie de session (supprimé à la fermeture)
            )

            response.set_cookie(
                key=auth_cookie_refresh_name,
                value=refresh_token,
                # --- CORRECTION : Utiliser max_age avec total_seconds() ---
                max_age=simple_jwt_config['REFRESH_TOKEN_LIFETIME'].total_seconds(),
                secure=auth_cookie_secure,
                httponly=auth_cookie_http_only, # Crucial pour la sécurité du refresh token
                samesite=auth_cookie_samesite,
                path=auth_cookie_path, # Souvent le même path mais peut être plus spécifique si besoin
                domain=auth_cookie_domain,
            )

            if simple_jwt_config.get('UPDATE_LAST_LOGIN', False):
                 update_last_login(None, user)

            return response

        else:
            # Authentification échouée
            return Response(
                {'detail': ('Identifiants invalides.')},
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """
    Gère la déconnexion de l'utilisateur en supprimant les cookies d'authentification
    et en ajoutant le refresh token à la liste noire si possible.
    """
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)

       
        simple_jwt_config = settings.SIMPLE_JWT

        auth_cookie_name = simple_jwt_config.get('AUTH_COOKIE')
        auth_cookie_refresh_name = simple_jwt_config.get('AUTH_COOKIE_REFRESH')
        auth_cookie_path = simple_jwt_config.get('AUTH_COOKIE_PATH', '/')
        auth_cookie_domain = simple_jwt_config.get('AUTH_COOKIE_DOMAIN', None)
        auth_cookie_samesite = simple_jwt_config["AUTH_COOKIE_SAMESITE"]

        if auth_cookie_name:
            response.delete_cookie(
                auth_cookie_name,
                path=auth_cookie_path,
                domain=auth_cookie_domain,
                samesite=auth_cookie_samesite,

            )

        if auth_cookie_refresh_name:
            response.delete_cookie(
                auth_cookie_refresh_name,
                path=auth_cookie_path,
                domain=auth_cookie_domain,
                samesite=auth_cookie_samesite,

            )

            try:
                refresh_token_value = request.COOKIES.get(auth_cookie_refresh_name)

                if refresh_token_value:
                    token = RefreshToken(refresh_token_value)
                    token.blacklist()

            except (TokenError, InvalidToken, KeyError, AttributeError, Exception) as e:
                pass

        return response


class UserProfileView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [CookieJWTAuthentication]

    def get(self, request, format=None):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)




class CookieTokenRefreshView(TokenRefreshView):
    """
    Subclasses TokenRefreshView to handle token refresh
    using HttpOnly cookies.
    """
    permission_classes = (AllowAny,) # No authentication needed, refresh token is the credential
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        simple_jwt_config = settings.SIMPLE_JWT

        # --- Get Cookie Settings ---
        refresh_cookie_name = simple_jwt_config["AUTH_COOKIE_REFRESH"]
        access_cookie_name = simple_jwt_config["AUTH_COOKIE"]
        auth_cookie_secure = simple_jwt_config["AUTH_COOKIE_SECURE"]
        auth_cookie_http_only = simple_jwt_config["AUTH_COOKIE_HTTP_ONLY"]
        auth_cookie_path = simple_jwt_config["AUTH_COOKIE_PATH"]
        auth_cookie_samesite = simple_jwt_config["AUTH_COOKIE_SAMESITE"]
        auth_cookie_domain = simple_jwt_config["AUTH_COOKIE_DOMAIN"]

        # --- Extract Refresh Token from Cookie ---
        refresh_token_value = request.COOKIES.get(refresh_cookie_name)
        if not refresh_token_value:
            return Response(
                {'detail': 'Refresh cookie not found.'},
                status=status.HTTP_401_UNAUTHORIZED # Or 400 Bad Request
            )

        # --- Use the Serializer to Validate and Generate New Tokens ---
        # We pass the refresh token from the cookie into the serializer's data
        serializer = self.get_serializer(data={'refresh': refresh_token_value})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # This catches expired tokens, blacklisted tokens, invalid format etc.
            # InvalidToken is a subclass of TokenError
            # simplejwt's default handler will return a 401 Unauthorized
            raise InvalidToken(e.args[0])

        # If validation is successful, serializer.validated_data contains the new tokens
        new_access_token = serializer.validated_data['access']
        # Check if a new refresh token was generated (rotation enabled)
        new_refresh_token = serializer.validated_data.get('refresh') # Use .get() as it might not be present

        # --- Prepare Response and Set Cookies ---
        # Don't return tokens in the body, just a success message or empty body
        response = Response({'detail': 'Token refreshed successfully.'}, status=status.HTTP_200_OK)

        # Set the new access token cookie (typically session-based)
        response.set_cookie(
            key=access_cookie_name,
            value=new_access_token,
            httponly=auth_cookie_http_only,
            secure=auth_cookie_secure,
            samesite=auth_cookie_samesite,
            path=auth_cookie_path,
            domain=auth_cookie_domain,
            # No max_age/expires for session cookie behavior
        )

        # If rotation is enabled and a new refresh token was provided
        if new_refresh_token:
            response.set_cookie(
                key=refresh_cookie_name,
                value=new_refresh_token,
                max_age=simple_jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds(),
                httponly=auth_cookie_http_only,
                secure=auth_cookie_secure,
                samesite=auth_cookie_samesite,
                path=auth_cookie_path, # Often same path, adjust if needed
                domain=auth_cookie_domain,
            )
        # Note: If rotation is disabled, the original refresh token cookie remains valid
        # and we don't need to reset it unless we want to change its expiry,
        # which simplejwt doesn't do by default on refresh without rotation.

        return response

class CookieTokenVerifyView(APIView):
    """
    Vérifie la validité du token d'accès fourni via un cookie HttpOnly.

    Cette vue s'appuie sur la classe d'authentification configurée
    (par exemple, CookieJWTAuthentication) pour effectuer la validation
    lors du traitement initial de la requête par DRF.

    Si le code de la méthode get() ou post() est atteint, cela signifie que
    l'authentification a réussi et que le token est considéré comme valide
    (non expiré, signature correcte, utilisateur actif).
    """
    permission_classes = (IsAuthenticated,) # Crucial !

    def get(self, request, *args, **kwargs):
        """
        Gère les requêtes GET. Si on arrive ici, le token est valide.
        """
        user = request.user
        serialized_data = UserProfileSerializer(user)
        return Response({"detail": "Token is valid.", "user": serialized_data.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Gère les requêtes POST (alternative si préféré par le frontend).
        Si on arrive ici, le token est valide.
        """
        user = request.user
        serialized_data = UserProfileSerializer(user)

        return Response({"detail": "Token is valid.", "user": serialized_data.data}, status=status.HTTP_200_OK)



class PasswordResetRequestView(DynamicFormView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []
    success_message = _("Si un compte correspond à cet e-mail, un lien de réinitialisation a été envoyé.")
    # `success_url` n'est pas très pertinent ici car on n'effectue pas de redirection serveur.

    # Métadonnées pour le GET
    # Le titre et la description peuvent être définis ici ou dans la config de DynamicFormMetadata
    # si vous l'adaptez pour avoir des infos par vue/endpoint.
    # Pour simplifier, on les met ici pour la réponse GET de DynamicFormView.
    view_name = _("Demande de Réinitialisation de Mot de Passe")
    view_description = _("Veuillez entrer votre adresse e-mail pour recevoir un lien de réinitialisation.")


    def perform_action(self, serializer, request, *args, **kwargs):
        email = serializer.validated_data['email']
        active_users = UserModel.objects.filter(email__iexact=email, is_active=True)

        # Important : Boucler même s'il ne devrait y avoir qu'un seul utilisateur actif par email
        # pour éviter de confirmer si un email est enregistré. Toujours envoyer le même message de succès.
        for user in active_users: # En pratique, on s'attend à 0 ou 1 user
            # Utilisation du PasswordResetTokenGenerator de Django
            # uid = urlsafe_base64_encode(force_bytes(user.pk))
            # token = default_token_generator.make_token(user)
            # reset_path = reverse('password_reset_confirm_frontend', kwargs={'uidb64': uid, 'token': token}) # Nom de route frontend

            # Ou avec votre modèle PasswordResetToken personnalisé
            reset_token_obj = PasswordResetToken.objects.create(user=user)
            token_value = str(reset_token_obj.token) # L'UUID en string

            # L'URL que l'utilisateur recevra doit pointer vers VOTRE PAGE FRONTEND
            # qui gérera ensuite la confirmation avec le token.
            frontend_reset_url = f"{getattr(settings, 'FRONTEND_URL', 'https://cicaw.pythonanywhere.com')}" \
                                 f"/reset-password-confirm/{token_value}/" # Adaptez le chemin frontend
            
            context = {
                'user': user,
                'user_name': user.get_full_name() or user.username,
                'reset_password_url': frontend_reset_url,
            }
            try:
                if send_templated_email is None:
                    print("send_templated_email n'est pas disponible. Assurez-vous que le module notifications est installé.")
                    return {"email_sent": False} # Indiquer l'échec de l'envoi
                send_templated_email(
                    subject_template_name='notifications/email/user_auth/password_reset_subject.txt',
                    html_template_name='notifications/email/user_auth/password_reset_body.html',
                    context=context,
                    recipient_list=[user.email],
                    event_type='password_reset_request',
                    recipient_user=user,
                    related_object=user # ou reset_token_obj
                )
                print(f"Email de réinitialisation envoyé à {user.email} avec token {token_value}")
            except Exception as e:
                print(f"ERREUR envoi email de réinitialisation pour {user.email}: {e}")
                # Ne pas faire échouer la réponse pour l'utilisateur, l'erreur est loggée.
        
        # Toujours retourner un succès pour ne pas révéler si l'email existe
        # Le message de succès est défini dans `success_message` de la classe.
        # Le retour de `perform_action` est mis dans `data` par DynamicFormView
        return {"email_sent": True} # Juste un indicateur pour la réponse data si besoin



class PasswordResetConfirmView(DynamicFormView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []
    success_message = _("Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.")
    success_url = '/login' # URL de redirection frontend après succès

    view_name = _("Réinitialiser le Mot de Passe")
    view_description = _("Veuillez choisir un nouveau mot de passe.")
    
    # Stocker l'utilisateur et le token validés sur l'instance de la vue
    _valid_token_obj = None
    _user_to_reset = None

    def get_serializer_context(self):
        """Ajoute l'utilisateur au contexte du serializer pour la validation de la force du mot de passe."""
        context = super().get_serializer_context()
        if self._user_to_reset:
            context['user_for_password_validation'] = self._user_to_reset
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """
        Valide le token avant d'afficher/traiter le formulaire.
        Surcharge `dispatch` car la validation du token est une condition d'accès à la vue.
        """
        token_from_url = kwargs.get('token') # Le token est passé en paramètre d'URL
        if not token_from_url:
            # Le frontend ne devrait pas appeler cette vue sans token,
            # mais on peut retourner une page d'info.
            # DynamicFormView.get() s'en chargera si le serializer est vide.
            # Ou on lève une erreur que le frontend gère.
            # Pour cette approche, on va juste afficher un message dans le GET.
            return Response({"error":_("Token de réinitialisation manquant ou invalide.")}, status=status.HTTP_400_BAD_REQUEST)


        try:
            # Valider avec votre modèle PasswordResetToken
            self._valid_token_obj = PasswordResetToken.objects.get(token=token_from_url)
            if not self._valid_token_obj.is_valid():
                self._valid_token_obj = None # Marquer comme invalide pour le reste de la logique
                # On affichera un message via `get` au lieu de lever une exception ici
                # pour que le `DynamicFormView.get` puisse construire la réponse de métadonnées
                # avec un message d'erreur approprié.
                print(f"Token {token_from_url} invalide (expiré ou utilisé).")
            else:
                self._user_to_reset = self._valid_token_obj.user
                print(f"Token {token_from_url} valide pour l'utilisateur {self._user_to_reset.username}.")
        
        except PasswordResetToken.DoesNotExist:
            self._valid_token_obj = None
            print(f"Token {token_from_url} non trouvé.")
        except Exception as e:
            self._valid_token_obj = None
            print(f"Erreur validation token {token_from_url}: {e}")


        # La validation du token est cruciale ici. Si invalide, `get` devrait le gérer.
        # La méthode `get_object` de `DynamicFormView` n'est pas adaptée car on n'a pas de PK.
        return super().dispatch(request, *args, **kwargs)
    
    # Surcharger GET pour potentiellement ne pas afficher le formulaire si token invalide
    def get(self, request, *args, **kwargs):
        if not self._valid_token_obj or not self._user_to_reset:
            # Construire une réponse pour "token invalide" sans afficher le formulaire
            # La classe de métadonnées de DynamicFormView n'est pas utilisée ici car on ne rend pas de champs
            # DynamicFormView.get() utilise determine_metadata
            # On peut juste retourner une réponse formatée comme celle que le frontend attend.
            # Ou laisser DynamicFormView.get() le faire si on adapte determine_metadata.
            # Plus simple ici :
            return Response({
                "name": self.view_name,
                "description": _("Lien de réinitialisation invalide ou expiré."),
                "error": _("Ce lien de réinitialisation de mot de passe n'est plus valide. Veuillez refaire une demande."),
                "fields": [], # Pas de champs à afficher
                # Ajouter d'autres clés que le frontend pourrait attendre (display_form_fields: false)
                "display_form_fields": False, 
                "info_title": _("Lien Invalide"),
                "info_message": _("Ce lien de réinitialisation de mot de passe n'est plus valide."),
                "info_detail": _("Veuillez soumettre une nouvelle demande de réinitialisation si vous avez oublié votre mot de passe."),
                # "request_new_reset_link_url": reverse('password_reset_request_frontend_route_name')
            }, status=status.HTTP_200_OK) # Ou 400 si on veut une erreur client
        
        # Si token valide, laisser DynamicFormView.get() construire la réponse de métadonnées
        return super().get(request, *args, **kwargs)


    def perform_action(self, serializer, request, *args, **kwargs):
        # À ce stade, le token a déjà été validé dans `dispatch` (ou `get` si l'utilisateur vient d'arriver),
        # et `self._user_to_reset` et `self._valid_token_obj` devraient être définis si valides.
        if not self._user_to_reset or not self._valid_token_obj or not self._valid_token_obj.is_valid():
            # Double vérification ou si l'accès s'est fait directement en POST
            # On ne devrait pas arriver ici si `get` a bien filtré,
            # mais en cas d'appel POST direct sans GET préalable.
            raise PermissionDenied(_("Token de réinitialisation invalide ou expiré."))

        new_password = serializer.validated_data['new_password1']
        self._user_to_reset.set_password(new_password)
        self._user_to_reset.save(update_fields=['password']) # Sauvegarder uniquement le mot de passe
        
        self._valid_token_obj.mark_as_used() # Marquer le token comme utilisé
        print(f"Mot de passe réinitialisé pour {self._user_to_reset.username}. Token {self._valid_token_obj.token} marqué comme utilisé.")
        
        # Optionnel: Invalider toutes les sessions actives de l'utilisateur (pour la sécurité)
        # from django.contrib.auth import update_session_auth_hash
        # update_session_auth_hash(request, self._user_to_reset) # `request` est nécessaire

        # Le message de succès est déjà défini dans `success_message`
        # Le retour de `perform_action` est mis dans `data`
        return {"password_reset_complete": True}

# class PasswordResetView(APIView):
#     def post(self, request):
#         email = request.data.get('email').lower()
        
#         if User.objects.filter(email=email).exists():
#             user = User.objects.get(email=email)
#             token = default_token_generator.make_token(user)
#             uid = urlsafe_base64_encode(force_bytes(user.pk))

#             # Utiliser l'URL de l'environnement de déploiement
#             reset_url = f"{settings.FRONTEND_URL}/password-reset/{uid}/{token}"

#             # Contenu de l'email
#             subject = 'Réinitialisation de votre mot de passe'
#             message = (
#                 f"Bonjour,\n\n"
#                 f"Vous avez demandé une réinitialisation de votre mot de passe. "
#                 f"Veuillez cliquer sur le lien ci-dessous pour réinitialiser votre mot de passe :\n\n"
#                 f"{reset_url}\n\n"
#                 f"Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet email.\n\n"
#                 f"Merci,\n"
#                 f"L'équipe de support."
#             )

#             # Envoyer l'email
#             send_mail(
#                 subject,
#                 message,
#                 'webmaster@yourdomain.com',  # Remplacez par l'adresse de votre domaine
#                 [email],
#                 fail_silently=False,
#             )

#             return Response({'status': 1}, status=status.HTTP_200_OK)
#         return Response({'status': 0}, status=status.HTTP_200_OK)

# class SetNewPasswordView(FormModelSerializeView):
#     form = SetNewPasswordForm
#     permission_classes = [AllowAny]

#     def get(self, request, *arg, **kwargs):
#         uidb64 = kwargs.get("uidb64", "")
#         token = kwargs.get("token", "")
#         try:
#             uid = urlsafe_base64_decode(uidb64).decode()
#             user = User.objects.get(pk=uid)
#             if not default_token_generator.check_token(user, token):
#               return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
                
#         except User.DoesNotExist:
#           return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
        
#         return super().get(request, *arg, **kwargs)

#     def is_valid(self, request, data, *args, **kwargs):
#         uidb64 = kwargs.get("uidb64", "")
#         token = kwargs.get("token", "")
#         password = data.get("password")
#         try:
#             uid = urlsafe_base64_decode(uidb64).decode()
#             user = User.objects.get(pk=uid)

#             if default_token_generator.check_token(user, token):
#                 user.set_password(password)
#                 user.save()
#         except User.DoesNotExist:
#             return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
