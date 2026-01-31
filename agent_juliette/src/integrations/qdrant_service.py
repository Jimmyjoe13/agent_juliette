"""
Service d'intégration Qdrant.
Gère la connexion et les recherches dans la base vectorielle.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter

from src.config import get_settings
from src.integrations.openai_service import get_openai_service, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Résultat d'une recherche vectorielle."""
    id: str
    score: float
    content: str
    metadata: dict


class QdrantService:
    """
    Service pour interagir avec Qdrant.
    Gère les recherches vectorielles et l'indexation.
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Connexion à Qdrant Cloud
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = settings.qdrant_collection_name
        self.openai_service = get_openai_service()
        
        logger.info(f"Qdrant Service initialisé (collection: {self.collection_name})")
        
        # Vérification/création de la collection
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self) -> None:
        """Crée la collection si elle n'existe pas."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            logger.info(f"Création de la collection '{self.collection_name}'...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Collection '{self.collection_name}' créée avec succès")
        else:
            logger.debug(f"Collection '{self.collection_name}' existe déjà")
    
    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_metadata: dict | None = None,
    ) -> list[SearchResult]:
        """
        Recherche les documents les plus similaires à une requête.
        
        Args:
            query: La requête de recherche
            limit: Nombre maximum de résultats
            score_threshold: Score minimum de similarité (0-1)
            filter_metadata: Filtres optionnels sur les métadonnées
            
        Returns:
            Liste de SearchResult triés par score décroissant
        """
        # Génération de l'embedding de la requête
        query_embedding = self.openai_service.generate_embedding(query)
        
        # Construction du filtre si nécessaire
        qdrant_filter = None
        if filter_metadata:
            # TODO: Implémenter les filtres complexes si nécessaire
            pass
        
        # Recherche dans Qdrant
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )
        
        # Transformation des résultats
        search_results = []
        for hit in results:
            payload = hit.payload or {}
            search_results.append(SearchResult(
                id=str(hit.id),
                score=hit.score,
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
            ))
        
        logger.info(f"Recherche '{query[:50]}...' → {len(search_results)} résultats")
        
        return search_results
    
    def search_with_context(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> str:
        """
        Recherche et retourne le contexte formaté pour le RAG.
        
        Args:
            query: La requête de recherche
            limit: Nombre maximum de résultats
            score_threshold: Score minimum de similarité
            
        Returns:
            Contexte formaté en string pour injection dans le prompt
        """
        results = self.search(query, limit, score_threshold)
        
        if not results:
            logger.warning(f"Aucun résultat trouvé pour: {query[:50]}...")
            return ""
        
        # Formatage du contexte
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Document {i} - Score: {result.score:.2f}]\n{result.content}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Ajoute un document à la collection.
        
        Args:
            doc_id: Identifiant unique du document
            content: Contenu textuel à indexer
            metadata: Métadonnées associées
        """
        embedding = self.openai_service.generate_embedding(content)
        
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                "content": content,
                "metadata": metadata or {},
            },
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        
        logger.info(f"Document ajouté: {doc_id}")
    
    def add_documents_batch(
        self,
        documents: list[dict],
    ) -> None:
        """
        Ajoute plusieurs documents en batch.
        
        Args:
            documents: Liste de dicts avec 'id', 'content', et optionnellement 'metadata'
        """
        if not documents:
            return
        
        # Génération des embeddings en batch
        contents = [doc["content"] for doc in documents]
        embeddings = self.openai_service.generate_embeddings_batch(contents)
        
        # Création des points
        points = []
        for doc, embedding in zip(documents, embeddings):
            points.append(PointStruct(
                id=doc["id"],
                vector=embedding,
                payload={
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                },
            ))
        
        # Upsert en batch
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        
        logger.info(f"Batch de {len(documents)} documents ajoutés")
    
    def get_collection_info(self) -> dict:
        """Retourne les informations sur la collection."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }


@lru_cache
def get_qdrant_service() -> QdrantService:
    """Retourne une instance singleton du service Qdrant."""
    return QdrantService()
