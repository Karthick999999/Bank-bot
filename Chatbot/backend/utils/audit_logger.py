"""Audit logging utility for compliance traceability."""
import json
from backend.models.database import AuditModel


class AuditLogger:
    """Handles all audit logging for compliance and traceability."""
    
    @staticmethod
    def log_login(user_id, username, ip_address="", success=True):
        """Log a login attempt."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        AuditModel.log(
            user_id=user_id or "unknown",
            username=username,
            action=action,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_query(user_id, username, query, response, category="", confidence=0.0, sources=None, ip_address=""):
        """Log a chat query and response."""
        sources_str = json.dumps(sources or [])
        response_summary = response[:500] if response else ""
        AuditModel.log(
            user_id=user_id,
            username=username,
            action="CHAT_QUERY",
            query=query,
            response_summary=response_summary,
            category=category,
            confidence=confidence,
            sources=sources_str,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_search(user_id, username, query, results_count=0, ip_address=""):
        """Log a direct search."""
        AuditModel.log(
            user_id=user_id,
            username=username,
            action="DIRECT_SEARCH",
            query=query,
            response_summary=f"Found {results_count} results",
            ip_address=ip_address
        )
    
    @staticmethod
    def log_admin_action(user_id, username, action_detail, ip_address=""):
        """Log an admin action."""
        AuditModel.log(
            user_id=user_id,
            username=username,
            action="ADMIN_ACTION",
            query=action_detail,
            ip_address=ip_address
        )
    
    @staticmethod
    def get_logs(limit=200, user_id=None, action=None):
        """Retrieve audit logs."""
        return AuditModel.get_logs(limit=limit, user_id=user_id, action=action)
