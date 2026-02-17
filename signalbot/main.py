"""
Signal Shop Bot - Main Entry Point
Privacy-focused e-commerce platform with Monero integration
"""

import sys
import os
import signal
import tempfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from signalbot.database.db import DatabaseManager
from signalbot.models.seller import SellerManager
from signalbot.gui.wizard import SetupWizard
from signalbot.gui.dashboard import DashboardWindow
from signalbot.config.settings import DEBUG


def cleanup_temp_files():
    """
    Clean up orphaned libsignal temporary directories.
    This runs on graceful shutdown to prevent temp directory accumulation.
    """
    try:
        # Get TMPDIR from environment, default to system temp
        tmpdir = os.getenv('TMPDIR', tempfile.gettempdir())
        tmpdir_path = Path(tmpdir)
        
        if not tmpdir_path.exists():
            return
        
        # Find and remove libsignal directories
        cleaned_count = 0
        for item in tmpdir_path.glob('libsignal*'):
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    cleaned_count += 1
                    if DEBUG:
                        print(f"Cleaned up temp directory: {item}")
                except Exception as e:
                    if DEBUG:
                        print(f"Failed to clean up {item}: {e}")
        
        if cleaned_count > 0:
            print(f"\n✓ Cleaned up {cleaned_count} libsignal temp directories")
            
    except Exception as e:
        if DEBUG:
            print(f"Error during temp file cleanup: {e}")


# Global reference to dashboard for cleanup
_dashboard_instance = None


def signal_handler(signum, frame):
    """
    Handle SIGINT (Ctrl+C) and SIGTERM signals for graceful shutdown.
    """
    signal_names = {
        signal.SIGINT: 'SIGINT',
        signal.SIGTERM: 'SIGTERM'
    }
    signal_name = signal_names.get(signum, f'Signal {signum}')
    
    print(f"\n\nReceived {signal_name}, shutting down gracefully...")
    
    # Stop wallet RPC if available
    global _dashboard_instance
    if _dashboard_instance and hasattr(_dashboard_instance, 'wallet') and _dashboard_instance.wallet:
        try:
            if hasattr(_dashboard_instance.wallet, 'setup_manager') and _dashboard_instance.wallet.setup_manager:
                print("Stopping wallet RPC...")
                _dashboard_instance.wallet.setup_manager.stop_rpc()
        except Exception as e:
            print(f"Error stopping wallet RPC: {e}")
    
    # Clean up temp files
    cleanup_temp_files()
    
    # Exit
    sys.exit(0)


def main():
    """Main application entry point"""
    
    global _dashboard_instance
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Signal Shop Bot")
    
    try:
        # Initialize database with master password
        # In production, this would be derived from hardware or secure storage
        master_password = os.getenv("MASTER_PASSWORD", "default_master_key_change_me")
        
        db_manager = DatabaseManager(master_password)
        seller_manager = SellerManager(db_manager)
        
        # Check if setup needed
        if not seller_manager.seller_exists():
            # Run setup wizard
            wizard = SetupWizard(db_manager)
            if wizard.exec_() == SetupWizard.Accepted:
                # Setup completed, show dashboard
                if DashboardWindow.verify_pin(db_manager):
                    dashboard = DashboardWindow(db_manager)
                    _dashboard_instance = dashboard  # Store for signal handler
                    dashboard.show()
                else:
                    sys.exit(0)
            else:
                # Setup cancelled
                sys.exit(0)
        else:
            # Verify PIN and show dashboard
            if DashboardWindow.verify_pin(db_manager):
                dashboard = DashboardWindow(db_manager)
                _dashboard_instance = dashboard  # Store for signal handler
                dashboard.show()
            else:
                sys.exit(0)
        
        # Run application
        sys.exit(app.exec_())
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Application failed to start: {e}"
        )
        if DEBUG:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
