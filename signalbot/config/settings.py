"""
Configuration settings for Signal Shop Bot
"""

import os
from pathlib import Path


# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_DIR = DATA_DIR / "db"
WALLET_DIR = DATA_DIR / "wallet"
BACKUP_DIR = DATA_DIR / "backups"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)
WALLET_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# Database
DATABASE_FILE = DB_DIR / "shopbot.db"

# Security
MASTER_KEY_FILE = DATA_DIR / ".master_key"
PIN_HASH_FILE = DATA_DIR / ".pin_hash"

# Commission settings (DO NOT MODIFY)
COMMISSION_RATE = 0.07  # 7%

# Order settings
ORDER_EXPIRATION_MINUTES = 60  # Default order expiration time
LOW_STOCK_THRESHOLD = 5  # Alert when stock falls below this

# Messaging settings
MESSAGE_SEND_DELAY_SECONDS = 1  # Delay between bulk messages to avoid rate limiting

# Currency conversion
DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "NZD", "JPY"]

# Monero settings
MONERO_CONFIRMATIONS_REQUIRED = 10  # Number of confirmations for payment
PAYMENT_CHECK_INTERVAL = 30  # Seconds between payment checks

# Default Monero nodes for easy selection
# Note: Most public nodes use port 18081 for non-SSL and 18089 for SSL.
# These nodes are configured as specified in the requirements.
# Users can add custom nodes with SSL if preferred via the node management UI.
DEFAULT_NODES = [
    {'address': 'xmr-node.cakewallet.com', 'port': 18081, 'use_ssl': False, 'name': 'Cake Wallet', 'is_default': True},
    {'address': 'nodes.hashvault.pro', 'port': 18081, 'use_ssl': False, 'name': 'HashVault Pro'},
    {'address': 'node.supportxmr.com', 'port': 18081, 'use_ssl': False, 'name': 'SupportXMR'},
    {'address': 'node.moneroworld.com', 'port': 18081, 'use_ssl': False, 'name': 'MoneroWorld'},
    {'address': 'node.community.rino.io', 'port': 18081, 'use_ssl': False, 'name': 'Rino Community'},
    {'address': '127.0.0.1', 'port': 18081, 'use_ssl': False, 'name': 'Local Node'},
]

# Wallet RPC settings (for auto-managed wallets)
DEFAULT_RPC_PORT = 18082
DEFAULT_DAEMON_ADDRESS = 'node.moneroworld.com'
DEFAULT_DAEMON_PORT = 18089

# Node connection settings
NODE_CONNECTION_TIMEOUT = 30  # seconds
NODE_SYNC_TIMEOUT = 120  # seconds

# Signal settings
SIGNAL_DATA_DIR = DATA_DIR / "signal"
SIGNAL_DATA_DIR.mkdir(exist_ok=True)

# Image settings
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_FORMATS = ["JPEG", "PNG", "JPG"]
IMAGE_QUALITY = 85  # JPEG quality after compression

# Logging
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "shopbot.log"
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR

def should_log(level: str) -> bool:
    """Check if message should be logged based on current level"""
    levels = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3}
    return levels.get(level, 0) >= levels.get(LOG_LEVEL, 1)

# GUI settings
WINDOW_TITLE = "Signal Shop Bot - Seller Dashboard"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# API endpoints
XMR_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"

# Development mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
