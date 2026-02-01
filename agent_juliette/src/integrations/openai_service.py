"""
Service d'intégration OpenAI.
Gère les appels à l'API OpenAI pour les embeddings et les completions.
"""

import logging
from functools import lru_cache

from openai import OpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)

# Modèle d'embedding recommandé par OpenAI
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class OpenAIService:
    """
    Service pour interagir avec l'API OpenAI.
    Gère les embeddings et les completions.
    """
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        logger.info(f"OpenAI Service initialisé (modèle: {self.model})")
    
    def generate_embedding(self, text: str) -> list[float]:
        """
        Génère un embedding vectoriel pour un texte donné.
        
        Args:
            text: Le texte à vectoriser
            
        Returns:
            Liste de floats représentant le vecteur embedding
        """
        # Nettoyage du texte
        text = text.replace("\n", " ").strip()
        
        if not text:
            raise ValueError("Le texte ne peut pas être vide")
        
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Embedding généré: {len(embedding)} dimensions")
        
        return embedding
    
    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Génère des embeddings pour plusieurs textes en une seule requête.
        
        Args:
            texts: Liste de textes à vectoriser
            
        Returns:
            Liste de vecteurs embeddings
        """
        # Nettoyage des textes
        cleaned_texts = [t.replace("\n", " ").strip() for t in texts if t.strip()]
        
        if not cleaned_texts:
            return []
        
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=cleaned_texts,
        )
        
        embeddings = [item.embedding for item in response.data]
        logger.debug(f"Batch embeddings générés: {len(embeddings)} vecteurs")
        
        return embeddings
    
    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        Génère une completion de texte via GPT.
        
        Args:
            prompt: Le prompt utilisateur
            system_prompt: Instructions système optionnelles
            context: Contexte RAG optionnel à inclure
            max_tokens: Nombre maximum de tokens en sortie
            temperature: Créativité (0-1)
            
        Returns:
            Le texte généré
        """
        messages = []
        
        # Prompt système
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Ajout du contexte RAG si fourni
        if context:
            messages.append({
                "role": "system",
                "content": f"Voici des informations contextuelles pertinentes:\n\n{context}"
            })
        
        # Prompt utilisateur
        messages.append({"role": "user", "content": prompt})
        
        # Construction des paramètres de base
        params = {
            "model": self.model,
            "messages": messages,
        }
        
        # Détermination des paramètres selon le modèle
        # Certains modèles (o1, gpt-5-nano) ne supportent pas temperature
        # et utilisent max_completion_tokens au lieu de max_tokens
        model_lower = self.model.lower()
        is_reasoning_model = any(m in model_lower for m in ['o1', 'o3', 'gpt-5'])
        
        if is_reasoning_model:
            # Modèles de raisonnement: pas de temperature, max_completion_tokens
            params["max_completion_tokens"] = max_tokens
        else:
            # Autres modèles: temperature supporté
            params["max_completion_tokens"] = max_tokens
            params["temperature"] = temperature
        
        try:
            response = self.client.chat.completions.create(**params)
        except Exception as e:
            error_msg = str(e).lower()
            # Fallback si le paramètre n'est pas supporté
            if "max_completion_tokens" in error_msg:
                params.pop("max_completion_tokens", None)
                params["max_tokens"] = max_tokens
                response = self.client.chat.completions.create(**params)
            elif "temperature" in error_msg:
                params.pop("temperature", None)
                response = self.client.chat.completions.create(**params)
            else:
                raise
        
        content = response.choices[0].message.content
        logger.debug(f"Completion générée: {len(content)} caractères")
        
        return content


@lru_cache
def get_openai_service() -> OpenAIService:
    """Retourne une instance singleton du service OpenAI."""
    return OpenAIService()
