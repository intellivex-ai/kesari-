"""
Kesari AI — Vector Memory
RAG-powered contextual memory using ChromaDB for semantic search.
"""
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class VectorMemory:
    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._init_db()

    def _init_db(self):
        try:
            import chromadb
            
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Get or create our main collection
            self.collection = self.client.get_or_create_collection(
                name="kesari_longterm_memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Vector memory initialized at {self.persist_directory}")
        except ImportError as e:
            logger.error(f"chromadb not installed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Vector Memory: {e}")

    def add_memory(self, memory_id: str, text: str, metadata: dict = None):
        """Add a memory fragment to the vector database."""
        if not self.collection:
            return

        try:
            # ChromaDB requires at least one metadata field
            safe_meta = {"source": "kesari"}
            if metadata:
                safe_meta.update(metadata)

            self.collection.add(
                documents=[text],
                metadatas=[safe_meta],
                ids=[memory_id]
            )
            logger.info(f"Added memory to vector db: {memory_id}")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant memories based on the query."""
        if not self.collection:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format the output
            if not results or not results["documents"] or not results["documents"][0]:
                return []
                
            formatted_results = []
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
            ids = results["ids"][0]
            
            for i in range(len(documents)):
                formatted_results.append({
                    "id": ids[i],
                    "content": documents[i],
                    "metadata": metadatas[i]
                })
                
            return formatted_results
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []
