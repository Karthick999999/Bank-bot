"""Run the Banking Knowledge Chatbot application."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
from backend.config import Config

if __name__ == "__main__":
    print("=" * 60)
    print("  Banking Knowledge Chatbot - Starting...")
    print("=" * 60)
    
    # Initialize vector store (this downloads the model on first run)
    print("[Startup] Initializing vector store...")
    from backend.knowledge.vector_store import VectorStore
    VectorStore.get_instance()
    
    app = create_app()
    
    print(f"\n{'=' * 60}")
    print(f"  Server running at: http://localhost:{Config.PORT}")
    print(f"  Login page: http://localhost:{Config.PORT}/")
    print(f"  Chat page:  http://localhost:{Config.PORT}/chat")
    print(f"  Admin page: http://localhost:{Config.PORT}/admin")
    print(f"{'=' * 60}\n")
    print("  Default Credentials:")
    print("  admin/admin123 | ops_user/ops123 | compliance/comp123 | support/support123")
    print(f"{'=' * 60}\n")
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
