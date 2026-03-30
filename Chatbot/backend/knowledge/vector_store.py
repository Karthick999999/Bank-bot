"""ChromaDB Vector Store management for banking knowledge base."""
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from backend.config import Config
from backend.knowledge.banking_kb import get_all_documents


class VectorStore:
    """Manages ChromaDB vector store for semantic search."""
    
    _instance = None
    _model = None
    _collection = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize embedding model and ChromaDB."""
        print("[VectorStore] Loading embedding model...")
        self._model = SentenceTransformer(Config.EMBEDDING_MODEL)
        print("[VectorStore] Embedding model loaded.")
        
        os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=Config.CHROMA_PERSIST_DIR)
        
        existing = [c.name for c in self._client.list_collections()]
        if Config.COLLECTION_NAME in existing:
            self._collection = self._client.get_collection(
                name=Config.COLLECTION_NAME,
                embedding_function=None
            )
            print(f"[VectorStore] Loaded existing collection with {self._collection.count()} documents.")
            if self._collection.count() == 0:
                self._ingest_knowledge_base()
        else:
            self._collection = self._client.create_collection(
                name=Config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            self._ingest_knowledge_base()
    
    def _ingest_knowledge_base(self):
        """Ingest all banking knowledge base documents."""
        documents = get_all_documents()
        print(f"[VectorStore] Ingesting {len(documents)} documents...")
        
        ids = []
        texts = []
        metadatas = []
        embeddings = []
        
        for doc in documents:
            full_text = f"{doc['title']}. {doc['content']}"
            ids.append(doc["id"])
            texts.append(full_text)
            metadatas.append({
                "title": doc["title"],
                "category": doc["category"],
                "access_level": doc["access_level"],
                "doc_id": doc["id"],
            })
            embeddings.append(self._model.encode(full_text).tolist())
        
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self._collection.add(
                ids=ids[i:end],
                documents=texts[i:end],
                metadatas=metadatas[i:end],
                embeddings=embeddings[i:end],
            )
        
        print(f"[VectorStore] Ingested {len(ids)} documents successfully.")
    
    def search(self, query, top_k=None, category_filter=None, access_filter=None):
        """Semantic search over the knowledge base."""
        top_k = top_k or Config.TOP_K_RESULTS
        query_embedding = self._model.encode(query).tolist()
        
        where_filter = None
        if category_filter and access_filter:
            where_filter = {"$and": [
                {"category": {"$in": category_filter if isinstance(category_filter, list) else [category_filter]}},
            ]}
        elif category_filter:
            if isinstance(category_filter, list):
                where_filter = {"category": {"$in": category_filter}}
            else:
                where_filter = {"category": category_filter}
        
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        
        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                similarity = 1 - distance
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                search_results.append({
                    "content": doc,
                    "similarity": round(similarity, 4),
                    "title": metadata.get("title", ""),
                    "category": metadata.get("category", ""),
                    "doc_id": metadata.get("doc_id", ""),
                    "access_level": metadata.get("access_level", "general"),
                })
        
        return search_results
    
    def get_stats(self):
        """Return vector store statistics."""
        return {
            "total_vectors": self._collection.count() if self._collection else 0,
            "embedding_model": Config.EMBEDDING_MODEL,
            "collection_name": Config.COLLECTION_NAME,
        }
    
    def reingest(self):
        """Re-ingest all documents (useful after KB update)."""
        try:
            self._client.delete_collection(Config.COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.create_collection(
            name=Config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self._ingest_knowledge_base()
