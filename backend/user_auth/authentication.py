from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.conf import settings

class CookieJWTAuthentication(JWTAuthentication):
    """
    Authentification JWT personnalisée qui lit le token d'accès
    depuis un cookie HTTP Only spécifié dans les settings.
    """
    def authenticate(self, request):
        # Récupère le nom du cookie d'accès depuis les settings
        access_cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE')
        if not access_cookie_name:
            # Si le nom du cookie n'est pas configuré, on ne peut rien faire
            return None

        # Tente de lire le token brut depuis le cookie
        raw_token = request.COOKIES.get(access_cookie_name)
        if raw_token is None:
            # Si le cookie n'est pas présent, l'authentification échoue pour cette méthode
            return None

        try:
            # Valide le token en utilisant la logique héritée
            validated_token = self.get_validated_token(raw_token)
             # Récupère l'utilisateur associé au token validé
            user = self.get_user(validated_token)
        except InvalidToken as e:
            # Log l'erreur si nécessaire
            print(f"CookieJWTAuthentication: Invalid token found in cookie '{access_cookie_name}'. Error: {e}")
            # Important : Ne pas lever AuthenticationFailed ici directement si on veut
            # potentiellement permettre à d'autres méthodes d'auth de s'exécuter.
            # Retourner None signifie que CETTE méthode n'a pas pu authentifier.
            # Si c'est la SEULE méthode, alors lever l'exception est aussi une option,
            # mais retourner None est plus flexible si on a plusieurs classes d'auth.
            # Cependant, pour un 401 clair si le cookie existe mais est invalide :
            raise AuthenticationFailed(f"Token invalide ou expiré dans le cookie.", code='invalid_token_cookie')

        except Exception as e:
            # Gérer d'autres erreurs potentielles (ex: user not found, etc.)
            print(f"CookieJWTAuthentication: Error during authentication. Error: {e}")
            raise AuthenticationFailed("Erreur pendant la validation du token cookie.")

        if not user or not user.is_active:
             raise AuthenticationFailed("Utilisateur inactif ou introuvable.", code='user_not_found_or_inactive')

        # Si tout réussit, retourne l'utilisateur et le token validé
        # C'est ce qui définit request.user et request.auth
        return (user, validated_token)