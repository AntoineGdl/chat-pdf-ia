import numpy as np
from numpy import ndarray, dtype, float64
from sentence_transformers import SentenceTransformer
from typing import List

from torch import Tensor


class EmbeddingStore:
    """Gestion des embeddings pour la recherche sémantique"""

    def __init__(self):
        # Modèle léger multilingue
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def create_embedding(self, text: str) -> ndarray[tuple[int], dtype[float64]] | Tensor:
        """Crée un embedding vectoriel à partir d'un texte"""
        if not text or len(text) < 10:
            return np.zeros(384)  # Dimension du modèle
        return self.model.encode(text)

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux embeddings"""
        if np.all(embedding1 == 0) or np.all(embedding2 == 0):
            return 0.0

        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        return float(similarity)