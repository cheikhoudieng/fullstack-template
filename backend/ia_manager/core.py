from django.conf import settings
from ia_manager.models import IAInteraction
from ia_manager.providers import GeminiProvider



class AIManager:
    """Gestionnaire principal d'IA"""
    
    def __init__(self, provider_name=None):
        self.provider = self._get_provider(provider_name or settings.DEFAULT_AI_PROVIDER)
        
    def _get_provider(self, provider_name):
        providers = {
            'gemini': GeminiProvider,
            #'openai': OpenAIProvider,
            # Ajouter d'autres fournisseurs ici
        }
        return providers[provider_name]()
    
    def process_request(self, user, prompt, system_instruction=None, **kwargs):
        """Point d'entrée principal pour les requêtes IA"""
        
        try:
            response_data = self.provider.generate_content(prompt, system_instruction, **kwargs)

            if not response_data or not response_data.get('processed_response'):
                # Cela peut arriver si Gemini bloque la réponse pour des raisons de sécurité.
                # Nous le traitons comme une erreur.
                print(response_data)
                raise ValueError("La réponse de l'IA est vide, potentiellement bloquée par les filtres de sécurité.")

            return self._handle_response(user, response_data)

        except Exception as e:
            return self._handle_error(user, e)
    

    
    # def _process_image(self, image_file):
    #     # Convertir l'image en base64 ou autre format requis
    #     if isinstance(image_file, str):  # Si c'est déjà un chemin
    #         with open(image_file, "rb") as image_file:
    #             return base64.b64encode(image_file.read()).decode('utf-8')
        # return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _handle_response(self, user, response):
        # Logging de l'interaction
        IAInteraction.objects.create(
            user=user,
            model_name=self.provider.get_model_info(),
            input_data=response.get('input_data'),
            output_data=response.get('output_data'),
            metadata=response.get('metadata')
        )
        return response.get('processed_response')
    
    def _handle_error(self, user, error):
        # Logging des erreurs
        IAInteraction.objects.create(
            user=user,
            model_name=self.provider.get_model_info(),
            error=str(error)
        )
        raise AIProcessingError(f"AI request failed: {str(error)}")

class AIProcessingError(Exception):
    pass

# Exemple d'implémentation d'un fournisseur