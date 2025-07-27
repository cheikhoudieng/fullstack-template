

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.conf import settings # Pour accéder aux noms des cookies JWT

from django.conf import settings as test_runner_settings
import pprint

print("\n--- DEBUG [test_auth_views.py]: Settings loaded by test runner ---")
if hasattr(test_runner_settings, 'SIMPLE_JWT'):
    print("SIMPLE_JWT found:")
    pprint.pprint(test_runner_settings.SIMPLE_JWT)
else:
    print("SIMPLE_JWT NOT FOUND in settings seen by test runner!")
print("--- DEBUG END ---\n")

User = get_user_model()

# Utiliser les noms de cookies définis dans settings.SIMPLE_JWT
ACCESS_COOKIE_NAME = settings.SIMPLE_JWT['AUTH_COOKIE']
REFRESH_COOKIE_NAME = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']

class AuthIntegrationTests(APITestCase):
    """
    Suite de tests couvrant l'ensemble du flux d'authentification
    en utilisant le client API de DRF et les cookies httpOnly.
    """

    @classmethod
    def setUpTestData(cls):
        """Crée des données de base une seule fois pour toute la classe."""
        cls.register_url = reverse('register')
        cls.csrf_url = reverse('get_csrf')
        cls.login_url = reverse('token_obtain_pair')
        cls.logout_url = reverse('logout')
        cls.profile_url = reverse('user_profile')
        cls.refresh_url = reverse('token_refresh')
        cls.verify_url = reverse('token_verify')

        # Données utilisateur valides pour les tests
        cls.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'strongPassword123',
            'password2': 'strongPassword123',
        }
        # Données utilisateur invalides
        cls.invalid_user_data_password_mismatch = {
            **cls.valid_user_data,
            'password2': 'wrongPassword',
        }
        cls.invalid_user_data_missing_field = {
             'email': 'test@example.com',
             'first_name': 'Test',
             'last_name': 'User',
             'password': 'strongPassword123',
             'password2': 'strongPassword123',
        }
         # Créer un utilisateur existant pour les tests de login/unicité
        cls.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='existingPassword',
            full_name='Existing User'
        )

    def setUp(self):
        """
        S'exécute avant chaque test. Crée un nouveau client pour l'isolation.
        Force la vérification CSRF.
        """
        self.client = APIClient(enforce_csrf_checks=True)
        # Obtient un token CSRF initial pour les tests POST suivants
        # La première requête GET définit le cookie csrftoken pour le client
        self.client.get(self.csrf_url)

    # --- Tests CSRF ---
    def test_get_csrf_token(self):
        """Vérifie que l'endpoint CSRF fonctionne et retourne le token."""
        response = self.client.get(self.csrf_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
        self.assertIsNotNone(response.data['csrfToken'])
        # Vérifie que le cookie 'csrftoken' est bien dans la réponse client (géré par APIClient)
        self.assertIn('csrftoken', self.client.cookies)

    # --- Tests d'Inscription (Register) ---
    def test_register_user_success(self):
        """Vérifie l'inscription réussie d'un nouvel utilisateur."""
        response = self.client.post(self.register_url, self.valid_user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK) # DynamicFormView renvoie 200 OK
        self.assertTrue(response.data.get('success'))
        self.assertIsNotNone(response.data.get('redirect_url')) # Vérifier si une URL de redirection est fournie

        # Vérifier en base de données
        self.assertTrue(User.objects.filter(username=self.valid_user_data['username']).exists())
        user = User.objects.get(username=self.valid_user_data['username'])
        self.assertEqual(user.email, self.valid_user_data['email'])
        # Vérifie que le signal a bien construit le full_name
        expected_full_name = f"{self.valid_user_data['first_name']} {self.valid_user_data['last_name']}"
        self.assertEqual(user.full_name, expected_full_name)
        # Vérifie que le mot de passe est haché (pas le brut)
        self.assertTrue(user.check_password(self.valid_user_data['password']))
        self.assertNotEqual(user.password, self.valid_user_data['password'])
        # Vérifie que le signal a défini une couleur de profil
        self.assertIsNotNone(user.profile_color)
        self.assertNotEqual(user.profile_color, '#362c54') # S'assurer qu'elle est différente de la valeur par défaut


    def test_register_user_password_mismatch(self):
        """Vérifie l'échec de l'inscription si les mots de passe ne correspondent pas."""
        response = self.client.post(self.register_url, self.invalid_user_data_password_mismatch, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('password2', response.data['errors']) # UserCreateSerializer met l'erreur sur password2
        self.assertFalse(User.objects.filter(username=self.invalid_user_data_password_mismatch['username']).exists())

    def test_register_user_missing_field(self):
        """Vérifie l'échec de l'inscription si un champ requis est manquant."""
        response = self.client.post(self.register_url, self.invalid_user_data_missing_field, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('username', response.data['errors']) # 'username' est manquant

    def test_register_user_duplicate_username(self):
        """Vérifie l'échec de l'inscription avec un username déjà pris."""
        data = {**self.valid_user_data, 'username': self.existing_user.username, 'email': 'unique@example.com'}
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('username', response.data['errors'])

    def test_register_user_duplicate_email(self):
        """Vérifie l'échec de l'inscription avec un email déjà pris."""
        data = {**self.valid_user_data, 'username': 'uniqueUser', 'email': self.existing_user.email}
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('email', response.data['errors'])

    def test_register_get_metadata(self):
        """Vérifie que GET sur /register retourne les métadonnées du formulaire."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('name', response.data) # DRF metadata standard
        self.assertIn('description', response.data)
        self.assertIn('renders', response.data)
        self.assertIn('parses', response.data)
       
        self.assertIn('fields', response.data) # Vérifier directement la clé 'fields'
        fields_data = {field['name']: field for field in response.data['fields']} # Utiliser 'fields'
        self.assertIn('username', fields_data)
        self.assertIn('email', fields_data)

    # --- Tests de Connexion (Login) ---
    def test_login_success(self):
        """Vérifie la connexion réussie et la réception des cookies JWT."""
        login_data = {
            'username': self.existing_user.username,
            'password': 'existingPassword',
        }
        response = self.client.post(self.login_url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Vérifie les données utilisateur dans la réponse
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['id'], self.existing_user.id)
        self.assertEqual(response.data['user']['username'], self.existing_user.username)
        self.assertEqual(response.data['user']['email'], self.existing_user.email)
        self.assertEqual(response.data['user']['full_name'], self.existing_user.full_name)

        # Vérifie la présence et les attributs des cookies JWT dans la *réponse*
        self.assertIn(ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)

        access_cookie = response.cookies[ACCESS_COOKIE_NAME]
        refresh_cookie = response.cookies[REFRESH_COOKIE_NAME]

        self.assertTrue(access_cookie['httponly'])
        # access_cookie ne devrait pas avoir de max-age pour être un cookie de session
        self.assertEqual(access_cookie['max-age'], '')
        self.assertEqual(access_cookie['samesite'], settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
        # Vérifiez 'secure' basé sur vos settings
        self.assertEqual(access_cookie['secure'], settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'])

        self.assertTrue(refresh_cookie['httponly'])
        self.assertNotEqual(refresh_cookie['max-age'], '') # Doit avoir une expiration
        expected_refresh_max_age = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
        # Attention: Il peut y avoir un très léger écart, tester la proximité ou caster en int.
        self.assertAlmostEqual(int(refresh_cookie['max-age']), int(expected_refresh_max_age), delta=2)
        self.assertEqual(refresh_cookie['samesite'], settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
        self.assertEqual(refresh_cookie['secure'], settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'])

        # Vérifie que les cookies sont stockés sur le *client* pour les prochaines requêtes
        self.assertIn(ACCESS_COOKIE_NAME, self.client.cookies)
        self.assertIn(REFRESH_COOKIE_NAME, self.client.cookies)

    def test_login_invalid_password(self):
        """Vérifie l'échec de connexion avec un mot de passe incorrect."""
        login_data = {
            'username': self.existing_user.username,
            'password': 'wrongPassword',
        }
        response = self.client.post(self.login_url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Nom d\'utilisateur ou mot de passe invalide.')
        # Vérifie qu'aucun cookie n'a été défini
        self.assertNotIn(ACCESS_COOKIE_NAME, response.cookies)
        self.assertNotIn(REFRESH_COOKIE_NAME, response.cookies)

    def test_login_nonexistent_user(self):
        """Vérifie l'échec de connexion avec un utilisateur inexistant."""
        login_data = {
            'username': 'nonexistentuser',
            'password': 'anyPassword',
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Géré par l'exception générique
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Nom d\'utilisateur ou mot de passe invalide.')
         # Vérifie qu'aucun cookie n'a été défini
        self.assertNotIn(ACCESS_COOKIE_NAME, response.cookies)
        self.assertNotIn(REFRESH_COOKIE_NAME, response.cookies)

    # --- Test Récupération Profil (Authentifié) ---
    def test_get_user_profile_authenticated(self):
        """Vérifie que le profil peut être récupéré après connexion."""
        # 1. Login
        login_data = {'username': self.existing_user.username, 'password': 'existingPassword'}
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.client.cookies.get(ACCESS_COOKIE_NAME)) # Confirme que le client a le cookie

        # 2. Requête authentifiée pour le profil
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['id'], self.existing_user.id)
        self.assertEqual(profile_response.data['username'], self.existing_user.username)
        self.assertEqual(profile_response.data['email'], self.existing_user.email)
        self.assertEqual(profile_response.data['full_name'], self.existing_user.full_name)

    def test_get_user_profile_unauthenticated(self):
        """Vérifie que le profil retourne 401 si non authentifié."""
        # Faire la requête SANS login préalable
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Tests de Déconnexion (Logout) ---
    def test_logout_success_authenticated(self):
        """Vérifie la déconnexion, suppression des cookies et blacklisting."""
        # 1. Login
        login_data = {'username': self.existing_user.username, 'password': 'existingPassword'}
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Récupère la valeur du refresh token qui vient d'être créée
        self.assertIn(REFRESH_COOKIE_NAME, self.client.cookies)
        refresh_token_value = self.client.cookies[REFRESH_COOKIE_NAME].value
        # Vérifier qu'il existe un token correspondant dans la DB
        self.assertTrue(OutstandingToken.objects.filter(token=refresh_token_value).exists())
        original_token_obj = OutstandingToken.objects.get(token=refresh_token_value)

        # 2. Logout
        logout_response = self.client.post(self.logout_url, {}, format='json') # Pas besoin de data
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)

        # 3. Vérifie la suppression des cookies dans la *réponse* logout
        self.assertIn(ACCESS_COOKIE_NAME, logout_response.cookies)
        self.assertIn(REFRESH_COOKIE_NAME, logout_response.cookies)
        # Les cookies supprimés ont max-age=0
        self.assertEqual(logout_response.cookies[ACCESS_COOKIE_NAME]['max-age'], 0)
        self.assertEqual(logout_response.cookies[REFRESH_COOKIE_NAME]['max-age'], 0)

        # 4. Vérifie que les cookies sont supprimés du *client*
        # Note: APIClient ne supprime pas automatiquement le cookie basé sur max-age=0 dans la réponse.
        # On peut vérifier qu'une nouvelle requête authentifiée échouerait,
        # ou vérifier explicitement le blacklistage ci-dessous.

        # 5. Vérifie le blacklisting du refresh token
        self.assertTrue(BlacklistedToken.objects.filter(token=original_token_obj).exists())

        # 6. Vérifie qu'une nouvelle requête vers un endpoint protégé échoue
        profile_response_after_logout = self.client.get(self.profile_url)
        self.assertEqual(profile_response_after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_unauthenticated(self):
        """Vérifie que logout retourne 204 même si l'utilisateur n'était pas loggué."""
        # Pas de login avant
        logout_response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
         # Il essaiera de supprimer les cookies, mais ils n'existent pas
        self.assertIn(ACCESS_COOKIE_NAME, logout_response.cookies)
        self.assertIn(REFRESH_COOKIE_NAME, logout_response.cookies)
        self.assertEqual(logout_response.cookies[ACCESS_COOKIE_NAME]['max-age'], 0)
        self.assertEqual(logout_response.cookies[REFRESH_COOKIE_NAME]['max-age'], 0)


    # --- Tests de Rafraîchissement (Refresh) ---
    def test_token_refresh_success(self):
        """Vérifie le rafraîchissement réussi de l'access token."""
        # 1. Login
        login_data = {'username': self.existing_user.username, 'password': 'existingPassword'}
        self.client.post(self.login_url, login_data, format='json')
        original_access_token_value = self.client.cookies[ACCESS_COOKIE_NAME].value
        original_refresh_token_value = self.client.cookies[REFRESH_COOKIE_NAME].value
        self.assertTrue(original_access_token_value)
        self.assertTrue(original_refresh_token_value)

        # 2. Attendre un peu pour s'assurer que le nouveau token soit différent (si généré très vite)
        # import time
        # time.sleep(0.1)

        # 3. Refresh (le client envoie le refresh_cookie automatiquement)
        # Normalement, simplejwt refresh n'a pas besoin de payload si le cookie est utilisé
        refresh_response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

        # 4. Vérifie qu'un *nouvel* access token est dans la réponse cookie
        self.assertIn(ACCESS_COOKIE_NAME, refresh_response.cookies)
        new_access_token = refresh_response.cookies[ACCESS_COOKIE_NAME]
        self.assertNotEqual(new_access_token.value, original_access_token_value)
        self.assertTrue(new_access_token['httponly'])

        # 5. Vérifie le comportement pour le refresh token (rotation, blacklistage)
        # si ROTATE_REFRESH_TOKENS=True et BLACKLIST_AFTER_ROTATION=True
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            self.assertIn(REFRESH_COOKIE_NAME, refresh_response.cookies)
            new_refresh_token = refresh_response.cookies[REFRESH_COOKIE_NAME]
            self.assertNotEqual(new_refresh_token.value, original_refresh_token_value)
            self.assertTrue(new_refresh_token['httponly'])
            # Vérifier le blacklistage de l'ancien refresh token
            if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION'):
                old_outstanding = OutstandingToken.objects.get(token=original_refresh_token_value)
                self.assertTrue(BlacklistedToken.objects.filter(token=old_outstanding).exists())
        else:
             # Si la rotation est désactivée, le refresh cookie ne devrait pas être renvoyé
            self.assertNotIn(REFRESH_COOKIE_NAME, refresh_response.cookies)
            # Et l'ancien token ne devrait pas être blacklisté
            old_outstanding = OutstandingToken.objects.filter(token=original_refresh_token_value).first()
            if old_outstanding: # Peut avoir été supprimé par une action précédente
                self.assertFalse(BlacklistedToken.objects.filter(token=old_outstanding).exists())


        # 6. Vérifie que le client utilise le *nouvel* access token
        # (APIClient met à jour ses cookies automatiquement depuis la réponse)
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK) # Devrait fonctionner avec le nouveau token


    def test_token_refresh_no_refresh_cookie(self):
        """Vérifie l'échec du refresh si aucun cookie refresh n'est envoyé."""
        # Ne pas login avant
        refresh_response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh_invalid_refresh_cookie(self):
        """Vérifie l'échec du refresh avec un token invalide."""
         # Définir manuellement un cookie invalide
        self.client.cookies[REFRESH_COOKIE_NAME] = "invalidtokenvalue"
        refresh_response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_token_refresh_blacklisted_refresh_cookie(self):
        """Vérifie l'échec du refresh avec un token blacklisté (après logout)."""
        # 1. Login
        login_data = {'username': self.existing_user.username, 'password': 'existingPassword'}
        self.client.post(self.login_url, login_data, format='json')
        refresh_token_value = self.client.cookies[REFRESH_COOKIE_NAME].value # Garde la valeur

        # 2. Logout (blacklist le token)
        self.client.post(self.logout_url, {}, format='json')

        # 3. Essayer de rafraîchir avec le cookie (que le client *n'a plus*, mais on le remet pour le test)
        self.client.cookies[REFRESH_COOKIE_NAME] = refresh_token_value # Remettre le cookie blacklisté manuellement

        refresh_response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', refresh_response.data) # Doit indiquer que le token est blacklisté

    # --- Tests de Vérification (Verify) ---
    def test_token_verify_success(self):
        """Vérifie la vérification réussie d'un access token valide."""
        # 1. Login pour obtenir un access token
        login_data = {'username': self.existing_user.username, 'password': 'existingPassword'}
        self.client.post(self.login_url, login_data, format='json')
        access_token_value = self.client.cookies[ACCESS_COOKIE_NAME].value
        self.assertTrue(access_token_value)

        # 2. Verify (envoie le token dans le corps)
        verify_response = self.client.post(self.verify_url, {'token': access_token_value}, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        # La réponse devrait être un corps vide sur succès
        self.assertEqual(verify_response.content, b'{}') # ou b'' si le renderer est différent

    def test_token_verify_invalid_token(self):
        """Vérifie l'échec de la vérification avec un token invalide."""
        verify_response = self.client.post(self.verify_url, {'token': 'invalidtokenvalue'}, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', verify_response.data)

    # Ajouter des tests pour les cas d'access token expiré si vous pouvez facilement manipuler le temps
    # ou si SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] est très court pour les tests.