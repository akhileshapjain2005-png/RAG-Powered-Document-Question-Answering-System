"""Embedding model for generating vector representations of text."""

from typing import List, Union
import os
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingModel:
    """Wrapper for sentence transformer models to generate embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for input text(s).
        
        Args:
            texts: Single text string or list of text strings
            normalize: Whether to normalize embeddings to unit length
            
        Returns:
            Numpy array of embeddings (1D for single text, 2D for list)
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        
        return embeddings
    
    def encode_batch(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings
            batch_size: Number of texts to process at once
            normalize: Whether to normalize embeddings to unit length
            
        Returns:
            Numpy array of embeddings (2D)
        """
        return self.encode(texts, normalize=normalize)
