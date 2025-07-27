from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password 
from rest_framework.validators import UniqueValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError


User = get_user_model()


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        label="Nom d'utilisateur",
        help_text="Requis. 150 caractères ou moins. Lettres, chiffres et @/./+/-/_ seulement.",
        validators=[
            UnicodeUsernameValidator(), 
            UniqueValidator(queryset=User.objects.all(), message="Ce nom d'utilisateur est déjà pris.")
        ]
    )
    email = serializers.EmailField(
        max_length=254, # Longueur standard pour EmailField Django
        label="Adresse Email",
        validators=[
            UniqueValidator(queryset=User.objects.all(), message="Cette adresse email est déjà utilisée.")
        ]
    )
    first_name = serializers.CharField(
        max_length=150,
        required=True,
        label="Prénom",
        write_only=True
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        label="Nom de famille",
        write_only=True
        )
    password = serializers.CharField(
        write_only=True, # Ne pas inclure dans les réponses API
        required=True,
        style={'input_type': 'password'},
        label="Mot de passe",
        validators=[validate_password] 
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label="Confirmer le mot de passe"
    )

    def validate(self, data):
        if data['password'] != data['password2']:
             raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."}) # Cibler plutôt password2
        return data

    def create(self, validated_data):
        """
        Crée et retourne une nouvelle instance User avec full_name, étant donné les données validées.
        """
        validated_data.pop('password2')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')  

        full_name = f"{first_name} {last_name}".strip()

        validated_data['full_name'] = full_name

        try:
            user = User.objects.create_user(**validated_data)
            return user

        except TypeError as te:
            if 'full_name' in str(te):
                print(f"ERREUR: Le manager {User.objects.__class__.__name__} (ou create_user) ne semble pas accepter 'full_name'. Tentative alternative.")
                try:
                     user_data_alt = {
                         'username': validated_data['username'],
                         'email': validated_data['email'],
                         'full_name': validated_data['full_name'],
                         # 'is_staff', 'is_superuser', 'is_active' peuvent nécessiter des valeurs par défaut ici
                     }
                     user = User(**user_data_alt)
                     user.set_password(validated_data['password'])
                     user.save()
                     print("DEBUG: Utilisateur créé (alternative):", user, "avec full_name:", user.full_name)
                     return user
                except Exception as e_alt:
                      raise serializers.ValidationError({"non_field_errors": [f"Erreur (alt) lors de la création : {e_alt}"]})
            else:
                 raise te

        except Exception as e:
             raise serializers.ValidationError({"non_field_errors": [f"Erreur lors de la création : {e}"]})



class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', "profile_color", "full_name")


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Serializer personnalisé pour Token Refresh qui lit le refresh token
    depuis le cookie HTTP Only (spécifié dans SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
    au lieu de l'attendre dans le corps de la requête.
    """
    refresh = None # Indique qu'on n'attend plus ce champ explicitement dans les données d'entrée.

    def validate(self, attrs):
        # Récupère le nom du cookie refresh depuis les settings SIMPLE_JWT
        # Utilise 'refresh_token' comme valeur par défaut si non défini, mais il devrait l'être.
        refresh_cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')

        # Accède à la requête via le contexte passé par la vue
        request = self.context.get('request')
        if request is None:
             # Devrait normalement toujours être là si la vue le passe
             raise InvalidToken('Contexte de la requête manquant pour lire le cookie.')

        # Lit la valeur du cookie refresh
        refresh_token_value = request.COOKIES.get(refresh_cookie_name)

        if refresh_token_value is None:
            # Si le cookie refresh attendu n'est pas trouvé
            raise InvalidToken(
                f"Aucun token de rafraîchissement trouvé dans le cookie attendu ('{refresh_cookie_name}')."
            )

        # Injecte la valeur lue depuis le cookie dans les attributs 'attrs'
        # pour que la logique de validation parente puisse l'utiliser.
        attrs['refresh'] = refresh_token_value

        # Appelle la validation parente standard (qui vérifie la validité du token, etc.)
        # avec le token qu'on a injecté depuis le cookie.
        # C'est ici que la validation réelle du token a lieu.
        try:
            return super().validate(attrs)
        except InvalidToken as e:
            # Renvoyer une exception claire si la validation échoue
             raise InvalidToken(f"Le token du cookie '{refresh_cookie_name}' est invalide ou expiré. Détail: {e}")
        except Exception as e:
             # Capturer d'autres erreurs potentielles pendant la validation
             print(f"Erreur inattendue pendant super().validate: {e}")
             raise InvalidToken(f"Erreur serveur pendant la validation du refresh token.")







class LoginSerializer(serializers.Serializer):
    """
    Serializer pour la validation des données de connexion utilisateur.

    Détermine dynamiquement le champ identifiant requis (par exemple, 'email'
    ou 'username') en se basant sur le paramètre USERNAME_FIELD du modèle
    utilisateur personnalisé. Valide la présence et le format de base de
    l'identifiant et du mot de passe.
    """
   

    identifier = serializers.CharField(
        label=_("E-mail ou Nom d'utilisateur"), # Label explicite
        write_only=True, # Typiquement, on ne renvoie pas l'identifiant après connexion dans ce serializer
        required=True,
        allow_blank=False,
        help_text=_("Saisissez votre adresse e-mail ou votre nom d'utilisateur enregistré.")
    )
    password = serializers.CharField(
        label=_("Mot de passe"),
        style={'input_type': 'password'},
        write_only=True, # Le mot de passe ne doit jamais être renvoyé
        required=True,
        allow_blank=False,
        trim_whitespace=False # Pour les mots de passe, ne pas supprimer les espaces par défaut
    )

    def validate(self, attrs):
        # `attrs` contiendra {'identifier': 'valeur_saisie', 'password': 'mdp_saisi'}
        # La validation de l'existence de l'utilisateur et du mot de passe correct
        # se fera avec `django.contrib.auth.authenticate` dans la vue.
        # Ce serializer valide juste la présence et le format de base des champs.
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        if not identifier or not password: # Double vérification, bien que `required=True` devrait le faire
            raise serializers.ValidationError(
                _("L'identifiant et le mot de passe sont requis."), 
                code='authorization' # Code d'erreur pour une classification potentielle
            )
        
        # Optionnel : Vous pourriez ajouter ici une logique pour essayer de deviner si c'est un email
        # et le stocker sous une clé spécifique, mais c'est mieux géré par le backend d'authentification.
        # Par exemple :
        # if '@' in identifier:
        #     attrs['login_type'] = 'email'
        # else:
        #     attrs['login_type'] = 'username'
            
        return attrs


  


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('__all__')
        
    def to_representation(self, instance):
        """
        Custom representation to include the __str__ method.
        """
        representation = super().to_representation(instance)

        date_joined = instance.date_joined.strftime("%d %B %Y %H:%M")

        representation['date_joined'] = date_joined
        representation['str'] = str(instance)
        return representation





class UserProfileSerializer(serializers.ModelSerializer):
   
    

    class Meta:
        model = User
        fields = ['full_name', 'gender', 'email', 'is_superuser', 'profile_color', 'username']

    def get_is_seller(self, instance):
        if hasattr(instance, 'shop'):
            return instance.shop.is_approved
        else:
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['birthday'] = instance.birthday.strftime('%d %B %Y') if instance.birthday else ""

        return representation
    



class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(
        label=_("Adresse e-mail"),
        help_text=_("Saisissez l'adresse e-mail associée à votre compte."),
        required=True
    )

    def validate_email(self, value):
        # Vérifier si un utilisateur avec cet email existe ET est actif
        try:
            user = User.objects.get(email__iexact=value, is_active=True)
            # Stocker l'utilisateur trouvé dans le contexte du serializer pour la vue
            self.context['user_to_reset'] = user 
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe ou non pour des raisons de sécurité (énumération d'utilisateurs)
            # Mais pour la logique de la vue, on a besoin de savoir.
            # Ou bien, on valide juste le format et la vue fait la recherche.
            # Pour cet exemple, la vue fera la recherche.
            pass # On ne lève pas d'erreur ici pour ne pas confirmer l'existence de l'email.
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    # Le token sera dans l'URL, pas dans le corps de la requête normalement
    # Mais on peut l'inclure ici si le frontend doit le renvoyer
    # token = serializers.CharField(required=False, write_only=True) # Si besoin de le passer dans le corps

    new_password1 = serializers.CharField(
        label=_("Nouveau mot de passe"),
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        # Ajouter des validateurs de force de mot de passe ici si besoin (Django a des validateurs intégrés)
    )
    new_password2 = serializers.CharField(
        label=_("Confirmer le nouveau mot de passe"),
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password1'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password2": _("Les deux mots de passe ne correspondent pas.")})
        
        # Validation de la force du mot de passe (exemple utilisant les validateurs de Django)
        user_for_validation = self.context.get('user_for_password_validation') # Doit être passé par la vue
        if user_for_validation:
            try:
                from django.contrib.auth.password_validation import validate_password
                validate_password(attrs['new_password1'], user=user_for_validation)
            except DjangoValidationError as e:
                # `e.messages` est une liste de messages d'erreur
                raise serializers.ValidationError({"new_password1": list(e.messages)})
        return attrs