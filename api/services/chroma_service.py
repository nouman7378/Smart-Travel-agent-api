import os
import logging
from django.conf import settings

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

logger = logging.getLogger(__name__)

# Fast, lightweight model for sentence embeddings
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

class ChromaService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.collection_name = "travel_catalog"
        self.embedding_fn = None
        self._initialized = False
        self._init_error = None

        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.persist_dir = getattr(settings, 'CHROMADB_PERSIST_DIR', os.path.join(base_dir, 'chroma_db'))
        self.hf_home = os.path.join(base_dir, 'hf_cache')

    def ensure_initialized(self) -> bool:
        if self._initialized:
            return self.client is not None and self.collection is not None

        self._initialized = True

        if chromadb is None or embedding_functions is None:
            logger.warning("chromadb is not installed; vector search is disabled and chat will use fallback context only.")
            return False

        # Override HuggingFace cache directory to avoid Windows "Access Denied" on ~/.cache/huggingface
        os.environ['HF_HOME'] = self.hf_home

        os.makedirs(self.persist_dir, exist_ok=True)
        os.makedirs(self.hf_home, exist_ok=True)

        try:
            # Initialize persistent client only when vector search is actually needed.
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB initialized successfully at {self.persist_dir}")
            return True
        except Exception as e:
            self._init_error = e
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None
            return False

    def upsert_document(self, doc_id: str, text: str, metadata: dict = None):
        """Add or update a document in the vector store."""
        if not self.ensure_initialized():
            return

        if not self.collection:
            return
            
        try:
            self.collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[metadata] if metadata else None
            )
        except Exception as e:
            logger.error(f"Error upserting document {doc_id} to ChromaDB: {e}")

    def delete_document(self, doc_id: str):
        """Remove a document from the vector store."""
        if not self.ensure_initialized():
            return

        if not self.collection:
            return
            
        try:
            self.collection.delete(ids=[doc_id])
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} from ChromaDB: {e}")

    def query_documents(self, query: str, n_results: int = 5, where: dict = None):
        """
        Retrieve the most semantically relevant documents for a query.
        Returns a list of dicts: [{'id': str, 'document': str, 'metadata': dict, 'distance': float}]
        """
        if not self.ensure_initialized():
            return []

        if not self.collection:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # Format results into an easy-to-use list of dictionaries
            if not results.get('documents') or not results['documents'][0]:
                return []
                
            formatted_results = []
            for i in range(len(results['documents'][0])):
                # distance ranges from 0 (perfect match) to 2.0 (complete opposite) for cosine distance
                dist = results['distances'][0][i] if results.get('distances') else 0.0
                
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': dist
                })
                
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

# Singleton instance exported for use across the application
chroma_client = ChromaService()
