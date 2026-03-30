"""JWT Authentication and Role-Based Access Control."""
import jwt
import functools
from datetime import datetime, timedelta, timezone
from flask import request, jsonify

from backend.config import Config


def generate_token(user_data):
    """Generate a JWT token for authenticated user."""
    payload = {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "role": user_data["role"],
        "full_name": user_data["full_name"],
        "department": user_data.get("department", ""),
        "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token):
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid JWT token."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Authentication token is missing"}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated


def role_required(*roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            
            if user["role"] not in roles and "admin" not in [user["role"]]:
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def check_access(user_role, document_category):
    """Check if a user role has access to a document category."""
    role_config = Config.ROLES.get(user_role)
    if not role_config:
        return False
    
    if "all" in role_config["access"]:
        return True
    
    return document_category.lower() in role_config["access"] or document_category.lower() == "general"
