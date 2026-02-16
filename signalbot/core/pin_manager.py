"""
PIN Manager for Transaction Security
Handles PIN verification state and timeouts for secure transactions
"""

import time
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PINVerificationSession:
    """Represents a single PIN verification session"""
    
    def __init__(self, user_id: str, action: str, timeout_seconds: int = 60):
        """
        Initialize PIN verification session
        
        Args:
            user_id: User's Signal ID
            action: Action requiring PIN (e.g., 'send_transaction')
            timeout_seconds: Session timeout in seconds
        """
        self.user_id = user_id
        self.action = action
        self.created_at = datetime.now()
        self.timeout_seconds = timeout_seconds
        self.data = {}  # Store additional data like transaction details
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        expiry_time = self.created_at + timedelta(seconds=self.timeout_seconds)
        return datetime.now() > expiry_time
    
    def time_remaining(self) -> int:
        """Get remaining time in seconds"""
        expiry_time = self.created_at + timedelta(seconds=self.timeout_seconds)
        remaining = (expiry_time - datetime.now()).total_seconds()
        return max(0, int(remaining))


class PINManager:
    """Manages PIN verification sessions for transaction security"""
    
    def __init__(self):
        """Initialize PIN manager"""
        self.sessions: Dict[str, PINVerificationSession] = {}
    
    def create_session(
        self,
        user_id: str,
        action: str,
        timeout_seconds: int = 60,
        **data
    ) -> PINVerificationSession:
        """
        Create a new PIN verification session
        
        Args:
            user_id: User's Signal ID
            action: Action requiring PIN
            timeout_seconds: Session timeout in seconds
            **data: Additional data to store (e.g., transaction details)
            
        Returns:
            Created session
        """
        # Clean up any existing expired sessions
        self._cleanup_expired_sessions()
        
        # Create new session
        session = PINVerificationSession(user_id, action, timeout_seconds)
        session.data = data
        
        # Store session
        self.sessions[user_id] = session
        
        logger.info(f"Created PIN session for {user_id}: {action}")
        return session
    
    def get_session(self, user_id: str) -> Optional[PINVerificationSession]:
        """
        Get active PIN verification session for user
        
        Args:
            user_id: User's Signal ID
            
        Returns:
            Session if exists and not expired, None otherwise
        """
        session = self.sessions.get(user_id)
        
        if session is None:
            return None
        
        if session.is_expired():
            logger.info(f"PIN session expired for {user_id}")
            self.clear_session(user_id)
            return None
        
        return session
    
    def clear_session(self, user_id: str) -> bool:
        """
        Clear PIN verification session for user
        
        Args:
            user_id: User's Signal ID
            
        Returns:
            True if session was cleared, False if no session existed
        """
        if user_id in self.sessions:
            action = self.sessions[user_id].action
            del self.sessions[user_id]
            logger.info(f"Cleared PIN session for {user_id}: {action}")
            return True
        return False
    
    def has_active_session(self, user_id: str) -> bool:
        """
        Check if user has an active PIN verification session
        
        Args:
            user_id: User's Signal ID
            
        Returns:
            True if active session exists
        """
        return self.get_session(user_id) is not None
    
    def _cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired_users = [
            user_id for user_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for user_id in expired_users:
            logger.debug(f"Cleaning up expired PIN session for {user_id}")
            del self.sessions[user_id]


# Global PIN manager instance
pin_manager = PINManager()
