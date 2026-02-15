"""
Monero Node Health Monitor
Periodically checks node connectivity and auto-switches if needed
"""

import threading
import time
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class NodeHealthMonitor:
    """Monitors Monero node health and handles failover"""
    
    def __init__(self, wallet_setup_manager, check_interval: int = 300):
        """
        Args:
            wallet_setup_manager: WalletSetupManager instance
            check_interval: Seconds between health checks (default 5 minutes)
        """
        self.setup_manager = wallet_setup_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.backup_nodes = []
    
    def set_backup_nodes(self, nodes: List[Tuple[str, int]]):
        """Set backup nodes for failover"""
        self.backup_nodes = nodes
    
    def start(self):
        """Start health monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("✅ Node health monitor started")
    
    def stop(self):
        """Stop health monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped node health monitor")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Check RPC connection
                if not self.setup_manager.test_rpc_connection():
                    logger.warning("⚠️  RPC connection failed!")
                    self._handle_connection_failure()
                else:
                    logger.debug("✅ RPC connection healthy")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                time.sleep(60)  # Wait a minute on error
    
    def _handle_connection_failure(self):
        """Handle RPC connection failure with auto-recovery"""
        logger.warning("Attempting to recover connection...")
        
        # Try restarting RPC with current node
        if self.setup_manager.start_rpc():
            logger.info("✅ Reconnected to current node")
            return
        
        # Try backup nodes
        if self.backup_nodes:
            logger.info(f"Trying {len(self.backup_nodes)} backup nodes...")
            
            for address, port in self.backup_nodes:
                logger.info(f"Trying node {address}:{port}...")
                
                if self.setup_manager.start_rpc(daemon_address=address, daemon_port=port):
                    logger.info(f"✅ Connected to backup node: {address}:{port}")
                    # Update current node
                    self.setup_manager.daemon_address = address
                    self.setup_manager.daemon_port = port
                    return
        
        logger.error("❌ Failed to recover connection to any node")
