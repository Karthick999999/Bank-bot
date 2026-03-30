"""Configuration management for Banking Knowledge Chatbot."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "banking-chatbot-secret-key-2024")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    
    # Database
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "chatbot.db")
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-banking-secret-key-2024")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))
    
    # ChromaDB
    CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "data", "chromadb")
    COLLECTION_NAME = "banking_knowledge"
    
    # Embeddings
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # LLM (Optional - works without it)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_ENABLED = bool(os.getenv("GEMINI_API_KEY", "") or os.getenv("OPENAI_API_KEY", ""))
    
    # RAG Settings
    TOP_K_RESULTS = 5
    SIMILARITY_THRESHOLD = 0.25
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50
    
    # Audit
    AUDIT_LOG_ENABLED = True
    
    # RBAC Roles
    ROLES = {
        "admin": {"level": 4, "access": ["all"]},
        "compliance": {"level": 3, "access": ["compliance", "regulatory", "risk", "operations", "general"]},
        "operations": {"level": 2, "access": ["operations", "products", "customer_service", "general"]},
        "support": {"level": 1, "access": ["customer_service", "products", "digital_banking", "general"]},
    }
