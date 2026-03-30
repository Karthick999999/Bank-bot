"""Hybrid retriever combining semantic search with keyword matching."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from backend.config import Config
from backend.knowledge.vector_store import VectorStore
from backend.knowledge.banking_kb import get_all_documents


class HybridRetriever:
    """Combines semantic search (ChromaDB) with keyword search (TF-IDF)."""
    
    _tfidf_vectorizer = None
    _tfidf_matrix = None
    _documents = None
    
    @classmethod
    def initialize(cls):
        """Initialize TF-IDF index."""
        cls._documents = get_all_documents()
        corpus = [f"{doc['title']}. {doc['content']}" for doc in cls._documents]
        cls._tfidf_vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 2),
        )
        cls._tfidf_matrix = cls._tfidf_vectorizer.fit_transform(corpus)
        print(f"[Retriever] TF-IDF index built with {len(corpus)} documents.")
    
    @classmethod
    def keyword_search(cls, query, top_k=5):
        """TF-IDF keyword-based search."""
        if cls._tfidf_vectorizer is None:
            cls.initialize()
        
        query_vec = cls._tfidf_vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, cls._tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:
                doc = cls._documents[idx]
                results.append({
                    "content": f"{doc['title']}. {doc['content']}",
                    "similarity": round(float(similarities[idx]), 4),
                    "title": doc["title"],
                    "category": doc["category"],
                    "doc_id": doc["id"],
                    "access_level": doc["access_level"],
                    "source": "keyword",
                })
        return results
    
    @classmethod
    def hybrid_search(cls, query, top_k=None, category_filter=None, user_role="support"):
        """Combined semantic + keyword search with score fusion."""
        top_k = top_k or Config.TOP_K_RESULTS
        
        # Semantic search via ChromaDB
        vs = VectorStore.get_instance()
        semantic_results = vs.search(query, top_k=top_k, category_filter=category_filter)
        for r in semantic_results:
            r["source"] = "semantic"
        
        # Keyword search via TF-IDF
        keyword_results = cls.keyword_search(query, top_k=top_k)
        
        # Fuse results
        seen_ids = set()
        fused = []
        
        # Weighted combination: semantic gets 0.7, keyword gets 0.3
        for r in semantic_results:
            doc_id = r.get("doc_id", "")
            kw_match = next((kr for kr in keyword_results if kr.get("doc_id") == doc_id), None)
            
            if kw_match:
                combined_score = (r["similarity"] * 0.7) + (kw_match["similarity"] * 0.3)
                r["similarity"] = round(combined_score, 4)
                r["source"] = "hybrid"
            
            seen_ids.add(doc_id)
            fused.append(r)
        
        # Add keyword-only results
        for r in keyword_results:
            if r.get("doc_id") not in seen_ids:
                r["similarity"] = round(r["similarity"] * 0.3, 4)
                fused.append(r)
        
        # Sort by similarity
        fused.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Filter by similarity threshold
        fused = [r for r in fused if r["similarity"] >= Config.SIMILARITY_THRESHOLD]
        
        # Apply RBAC filtering
        from backend.auth.jwt_handler import check_access
        fused = [r for r in fused if check_access(user_role, r.get("category", "general"))]
        
        return fused[:top_k]
