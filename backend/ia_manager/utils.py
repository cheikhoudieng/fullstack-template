import google.generativeai as genai
from google.generativeai.types import Content, Part, GenerateContentConfig, Schema, Type
from ia_manager.models import IAInteraction
import json
import logging
from io import BytesIO
from PIL import Image

# Clé API Gemini (⚠️ Stocke-la dans les variables d'environnement en prod)
API_KEY = "AIzaSyCDRYS84msbWLK6PZAi_1zS48j3P3B4TCc"

# Configurer l'API Gemini
genai.configure(api_key=API_KEY)

class IAManager:
    def __init__(self, model="gemini-2.0-flash", temperature=1, top_p=0.95, top_k=40):
        """Initialisation de la classe avec des paramètres configurables."""
        self.client = genai.Client(api_key=API_KEY)
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k

    def process_file(self, file):
        """
        Convertit un fichier en format compatible avec l'IA (ex: image en base64).
        """
        if isinstance(file, Image.Image):  # Image PIL
            buffer = BytesIO()
            file.save(buffer, format="JPEG", quality=60)
            buffer.seek(0)
            return buffer.read()  # Retourne les données binaires
        
        elif isinstance(file, bytes):  # Autre fichier binaire
            return file

        raise ValueError("Type de fichier non supporté")

    def ask(self, question, files=None, system_instruction="Réponds de manière détaillée."):
        """
        Envoie une question avec option d'ajouter des fichiers (ex: images).
        
        Args:
            - question (str): Texte de la question.
            - files (list): Liste d'objets (image, fichier binaire, etc.).
            - system_instruction (str): Instruction système pour l'IA.
        
        Returns:
            - dict: Réponse structurée de l'IA.
        """
        try:
            parts = [Part.from_text(question)]

            # Gestion des fichiers
            files_data = []
            if files:
                for file in files:
                    processed_file = self.process_file(file)
                    files_data.append(processed_file)
                    parts.append(Part.from_binary(processed_file, mime_type="image/jpeg"))

            # Configuration du prompt
            contents = [Content(role="user", parts=parts)]
            config = GenerateContentConfig(
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=Schema(
                    type=Type.OBJECT,
                    required=["is_valid", "response"],
                    properties={
                        "is_valid": Schema(type=Type.BOOLEAN),
                        "response": Schema(
                            type=Type.OBJECT,
                            required=["title", "description", "keywords"],
                            properties={
                                "title": Schema(type=Type.STRING),
                                "description": Schema(type=Type.STRING),
                                "keywords": Schema(type=Type.STRING),
                            },
                        ),
                    },
                ),
                system_instruction=[Part.from_text(system_instruction)],
            )

            # Envoi de la requête
            response_stream = self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )

            # Construire la réponse complète
            response_text = "".join([chunk.text for chunk in response_stream])
            response_data = json.loads(response_text)

            # Vérifier la validité de la réponse
            if not response_data.get("is_valid", False):
                logging.warning("Réponse non valide reçue de l'IA.")
                return {"error": "Réponse non valide."}

            # Enregistrer l'interaction dans la base de données
            interaction = IAInteraction.objects.create(
                question=question,
                response=json.dumps(response_data["response"], ensure_ascii=False),
                files=json.dumps(files_data) if files else None,
                model_used=self.model,
            )

            return response_data["response"]

        except Exception as e:
            logging.error(f"Erreur IA: {str(e)}")
            return {"error": "Erreur lors de la communication avec l'IA."}
