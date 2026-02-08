"""
Signal Shop Bot - Main Entry Point
Privacy-focused e-commerce platform with Monero integration
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from signalbot.database.db import DatabaseManager
from signalbot.models.seller import SellerManager
from signalbot.gui.wizard import SetupWizard
from signalbot.gui.dashboard import DashboardWindow
from signalbot.config.settings import DEBUG


def main():
    """Main application entry point"""
    
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
