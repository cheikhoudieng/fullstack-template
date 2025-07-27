
from abc import ABC, abstractmethod
from google import genai
from google.genai import types
from django.conf import settings



GEMINI_MODEL = "gemini-2.0-flash"

class AIProviderBase(ABC):
    """Interface de base pour les fournisseurs d'IA"""
    
    @abstractmethod
    def generate_content(self, prompt, system_instruction=None,  **kwargs):
        pass
    
    @abstractmethod
    def get_model_info(self):
        pass
    
class GeminiProvider(AIProviderBase):
    def generate_content(self,  prompt, system_instruction=None,model=GEMINI_MODEL, response_mime_type="application/json"):
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024,
                response_mime_type=response_mime_type
                ),
            contents=prompt,
        )

        
        
        return {
            'input_data': {'prompt': str(prompt), 'system_instruction': system_instruction},
            'output_data': response.text,
            'metadata': response.model_dump_json(),
            'processed_response': response.text
        }
    
    def get_model_info(self):
        return GEMINI_MODEL







"""
from ia_manager.core import AIManager
client = AIManager()
from user_auth.models  import User
user = User.objects.get(id=1)
client.process_request(user=user, prompt="salut", response_mime_type="application/json")
"""