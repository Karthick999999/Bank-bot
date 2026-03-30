"""Flask application - Banking Knowledge Chatbot API."""
import json
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from backend.config import Config
from backend.models.database import init_db, UserModel, ConversationModel, MessageModel
from backend.auth.jwt_handler import generate_token, token_required, role_required
from backend.rag.categorizer import categorize_query, get_search_categories
from backend.rag.retriever import HybridRetriever
from backend.rag.generator import generate_response
from backend.utils.audit_logger import AuditLogger
from backend.knowledge.banking_kb import get_kb_stats


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    CORS(app)
    
    # Initialize database
    init_db()
    print("[App] Database initialized.")
    
    # Initialize retriever
    HybridRetriever.initialize()
    print("[App] Hybrid retriever initialized.")
    
    # Frontend directory
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    
    # ==================== STATIC FILE SERVING ====================
    @app.route("/")
    def serve_index():
        return send_from_directory(frontend_dir, "login.html")
    
    @app.route("/chat")
    def serve_chat():
        return send_from_directory(frontend_dir, "index.html")
    
    @app.route("/admin")
    def serve_admin():
        return send_from_directory(frontend_dir, "admin.html")
    
    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(os.path.join(frontend_dir, "css"), filename)
    
    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(os.path.join(frontend_dir, "js"), filename)
    
    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        return send_from_directory(os.path.join(frontend_dir, "assets"), filename)
    
    # ==================== AUTH ENDPOINTS ====================
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        user = UserModel.authenticate(username, password)
        if not user:
            AuditLogger.log_login("unknown", username, request.remote_addr, success=False)
            return jsonify({"error": "Invalid credentials"}), 401
        
        token = generate_token(user)
        AuditLogger.log_login(user["id"], username, request.remote_addr, success=True)
        
        return jsonify({
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "department": user["department"],
            }
        })
    
    @app.route("/api/auth/register", methods=["POST"])
    @token_required
    @role_required("admin")
    def register():
        data = request.get_json()
        required = ["username", "password", "full_name", "role"]
        if not all(data.get(f) for f in required):
            return jsonify({"error": "Missing required fields"}), 400
        
        user_id = UserModel.create(
            data["username"], data["password"], data["full_name"],
            data["role"], data.get("department", "General"), data.get("email", "")
        )
        if not user_id:
            return jsonify({"error": "Username already exists"}), 409
        
        AuditLogger.log_admin_action(
            request.current_user["user_id"], request.current_user["username"],
            f"Created user: {data['username']} with role: {data['role']}"
        )
        return jsonify({"user_id": user_id, "message": "User created successfully"})
    
    @app.route("/api/auth/users", methods=["GET"])
    @token_required
    @role_required("admin")
    def get_users():
        users = UserModel.get_all()
        return jsonify({"users": users})
    
    # ==================== CHAT ENDPOINTS ====================
    @app.route("/api/chat", methods=["POST"])
    @token_required
    def chat():
        data = request.get_json()
        query = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")
        
        if not query:
            return jsonify({"error": "Message is required"}), 400
        
        user = request.current_user
        
        # Create new conversation if needed
        if not conversation_id:
            title = query[:50] + ("..." if len(query) > 50 else "")
            conversation_id = ConversationModel.create(user["user_id"], title)
        
        # Save user message
        MessageModel.add(conversation_id, "user", query)
        
        # Get chat history for context
        chat_history = MessageModel.get_recent_context(conversation_id, limit=6)
        
        # Categorize query
        categorization = categorize_query(query)
        
        # Retrieve relevant documents
        search_categories = get_search_categories(categorization) if categorization["category"] != "greeting" else None
        
        retrieved_docs = []
        if categorization["category"] != "greeting":
            retrieved_docs = HybridRetriever.hybrid_search(
                query, top_k=Config.TOP_K_RESULTS,
                category_filter=None,  # search across all for better results
                user_role=user["role"]
            )
        
        # Generate response
        result = generate_response(query, retrieved_docs, categorization, chat_history)
        
        # Save assistant message
        MessageModel.add(
            conversation_id, "assistant", result["response"],
            sources=json.dumps(result.get("sources", [])),
            category=result.get("category", ""),
            confidence=result.get("confidence", 0.0)
        )
        
        # Audit log
        AuditLogger.log_query(
            user["user_id"], user["username"], query, result["response"],
            category=result.get("category", ""),
            confidence=result.get("confidence", 0.0),
            sources=result.get("sources", []),
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "response": result["response"],
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.0),
            "category": result.get("category", ""),
            "conversation_id": conversation_id,
        })
    
    @app.route("/api/chat/conversations", methods=["GET"])
    @token_required
    def get_conversations():
        user = request.current_user
        convs = ConversationModel.get_by_user(user["user_id"])
        return jsonify({"conversations": convs})
    
    @app.route("/api/chat/history/<conversation_id>", methods=["GET"])
    @token_required
    def get_chat_history(conversation_id):
        messages = MessageModel.get_by_conversation(conversation_id)
        # Parse sources JSON
        for msg in messages:
            try:
                msg["sources"] = json.loads(msg.get("sources", "[]"))
            except (json.JSONDecodeError, TypeError):
                msg["sources"] = []
        return jsonify({"messages": messages})
    
    @app.route("/api/chat/new", methods=["POST"])
    @token_required
    def new_conversation():
        user = request.current_user
        conv_id = ConversationModel.create(user["user_id"])
        return jsonify({"conversation_id": conv_id})
    
    @app.route("/api/chat/conversations/<conversation_id>", methods=["DELETE"])
    @token_required
    def delete_conversation(conversation_id):
        ConversationModel.delete(conversation_id)
        return jsonify({"message": "Conversation deleted"})
    
    # ==================== KNOWLEDGE ENDPOINTS ====================
    @app.route("/api/knowledge/stats", methods=["GET"])
    @token_required
    def knowledge_stats():
        from backend.knowledge.vector_store import VectorStore
        kb_stats = get_kb_stats()
        vs_stats = VectorStore.get_instance().get_stats()
        return jsonify({**kb_stats, **vs_stats})
    
    @app.route("/api/knowledge/search", methods=["POST"])
    @token_required
    def search_knowledge():
        data = request.get_json()
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        user = request.current_user
        results = HybridRetriever.hybrid_search(query, top_k=10, user_role=user["role"])
        AuditLogger.log_search(user["user_id"], user["username"], query, len(results), request.remote_addr)
        return jsonify({"results": results, "count": len(results)})
    
    # ==================== AUDIT ENDPOINTS ====================
    @app.route("/api/audit/logs", methods=["GET"])
    @token_required
    @role_required("admin", "compliance")
    def get_audit_logs():
        limit = request.args.get("limit", 200, type=int)
        action = request.args.get("action", None)
        logs = AuditLogger.get_logs(limit=limit, action=action)
        return jsonify({"logs": logs, "count": len(logs)})
    
    # ==================== HEALTH ====================
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "Banking Knowledge Chatbot"})
    
    return app
