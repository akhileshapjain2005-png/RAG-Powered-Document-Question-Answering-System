
"""Vector store service for document embeddings and similarity search."""

from pathlib import Path
from typing import Dict, List, Optional

import chromadb
import numpy as np
from chromadb.config import Settings


class VectorStore:
    """Manage persistent document embeddings and similarity search."""

    def __init__(
        self,
        persist_directory: str = r"C:\RAG-DocQA-Chroma",
        collection_name: str = "documents",
    ):
        self.persist_directory = str(Path(persist_directory).resolve())
        self.collection_name = collection_name

        Path(self.persist_directory).mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        print(
            f"VECTOR STORE: Connected to {self.persist_directory}"
        )
        print(
            f"VECTOR STORE: Collection '{self.collection_name}' "
            f"contains {self.collection.count()} records"
        )

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Store document chunks, embeddings, and metadata."""

        if not texts:
            return []

        if len(texts) != len(metadatas):
            raise ValueError(
                "The number of texts must match the number of metadata records."
            )

        embeddings_array = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        if embeddings_array.ndim != 2:
            raise ValueError(
                "Embeddings must be a two-dimensional array."
            )

        if len(embeddings_array) != len(texts):
            raise ValueError(
                "The number of embeddings must match the number of text chunks."
            )

        if embeddings_array.shape[1] == 0:
            raise ValueError("Embedding vectors cannot be empty.")

        if not np.isfinite(embeddings_array).all():
            raise ValueError(
                "Embeddings contain NaN or infinite values."
            )

        if ids is None:
            ids = [
                f"doc_{i}_{metadatas[i].get('chunk_index', i)}"
                for i in range(len(texts))
            ]

        if len(ids) != len(texts):
            raise ValueError(
                "The number of IDs must match the number of text chunks."
            )

        if len(set(ids)) != len(ids):
            raise ValueError(
                "Document chunk IDs must be unique."
            )

        # ChromaDB requires string IDs and supported metadata values.
        if not all(isinstance(item, str) and item for item in ids):
            raise ValueError(
                "Every document chunk ID must be a non-empty string."
            )

        clean_metadatas = []

        for metadata in metadatas:
            if not isinstance(metadata, dict):
                raise ValueError(
                    "Every metadata record must be a dictionary."
                )

            clean_metadata = {}

            for key, value in metadata.items():
                if value is None:
                    continue

                if isinstance(value, np.generic):
                    value = value.item()

                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[str(key)] = value
                else:
                    clean_metadata[str(key)] = str(value)

            clean_metadatas.append(clean_metadata)

        print(
            f"VECTOR STORE DEBUG: path={self.persist_directory}, "
            f"collection={self.collection_name}, "
            f"chunks={len(texts)}, "
            f"dimensions={embeddings_array.shape[1]}"
        )

        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings_array.tolist(),
                documents=[str(text) for text in texts],
                metadatas=clean_metadatas,
            )

            print("VECTOR STORE DEBUG: Upsert completed.")

            stored_count = self.collection.count()

            print(
                f"VECTOR STORE DEBUG: Collection count={stored_count}"
            )

        except Exception as exc:
            print(
                f"VECTOR STORE ERROR: {type(exc).__name__}: {exc}"
            )
            raise

        return ids

    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search for chunks similar to a query embedding."""

        query_array = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if query_array.ndim == 1:
            query_array = query_array.reshape(1, -1)

        if query_array.ndim != 2 or query_array.shape[0] != 1:
            raise ValueError(
                "The query embedding must contain exactly one query vector."
            )

        if not np.isfinite(query_array).all():
            raise ValueError(
                "Query embedding contains NaN or infinite values."
            )

        if query_array.shape[1] != self.collection.metadata.get(
            "embedding_dimension",
            query_array.shape[1],
        ):
            raise ValueError("Invalid query embedding dimensions.")

        count = self.collection.count()

        if count == 0:
            return []

        query_arguments = {
            "query_embeddings": query_array.tolist(),
            "n_results": min(max(1, n_results), count),
            "include": ["documents", "metadatas", "distances"],
        }

        if filter_metadata:
            query_arguments["where"] = filter_metadata

        results = self.collection.query(**query_arguments)

        formatted_results = []

        result_ids = results.get("ids") or [[]]
        result_documents = results.get("documents") or [[]]
        result_metadatas = results.get("metadatas") or [[]]
        result_distances = results.get("distances") or [[]]

        for index, result_id in enumerate(result_ids[0]):
            documents = result_documents[0]
            metadatas = result_metadatas[0]
            distances = result_distances[0]

            formatted_results.append(
                {
                    "id": result_id,
                    "text": (
                        documents[index]
                        if index < len(documents)
                        and documents[index] is not None
                        else ""
                    ),
                    "metadata": (
                        metadatas[index]
                        if index < len(metadatas)
                        and metadatas[index] is not None
                        else {}
                    ),
                    "distance": (
                        distances[index]
                        if index < len(distances)
                        else None
                    ),
                }
            )

        return formatted_results

    def delete_documents(
        self,
        document_id: Optional[str] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> None:
        """Delete document chunks by ID or metadata filter."""

        if document_id:
            self.collection.delete(ids=[document_id])

        elif filter_metadata:
            self.collection.delete(where=filter_metadata)

        else:
            raise ValueError(
                "Provide either document_id or filter_metadata."
            )

    def get_collection_stats(self) -> Dict:
        """Return vector collection statistics."""

        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
        }
