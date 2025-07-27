from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 'username' ici peut être soit le nom d'utilisateur réel, soit l'email.
        # La vue LoginView passera la valeur saisie dans le champ 'username'
        # (ou ce qui est défini par UserModel.USERNAME_FIELD) ici.
        
        if username is None: # Si aucun identifiant n'est fourni
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if not username: # Encore une fois, s'assurer qu'on a quelque chose
            return None

        # Essayer de trouver l'utilisateur par nom d'utilisateur OU par email
        # On utilise Q object pour faire un OR dans la requête
        try:
            # On vérifie si l'identifiant fourni ressemble à un email
            # C'est une simple heuristique, une validation plus poussée de l'email
            # devrait être faite au niveau du formulaire/serializer d'inscription.
            if '@' in username:
                # On suppose que c'est un email. `i` pour insensible à la casse.
                user = UserModel.objects.get(Q(email__iexact=username) | Q(username__iexact=username))
            else:
                # On suppose que c'est un nom d'utilisateur
                user = UserModel.objects.get(Q(username__iexact=username))
        except UserModel.DoesNotExist:
            # Lancer UserModel.DoesNotExistS silencieusement ne révélera pas
            # si c'est le nom d'utilisateur ou le mot de passe qui est incorrect.
            return None
        except UserModel.MultipleObjectsReturned:
            # Cela ne devrait pas arriver si username et email sont uniques.
            # Mais si c'est le cas, c'est une erreur de données.
            return None 
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None # Authentification échouée