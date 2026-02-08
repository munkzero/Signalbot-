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

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Database
DATABASE_FILE = DB_DIR / "shopbot.db"

# Security
MASTER_KEY_FILE = DATA_DIR / ".master_key"
PIN_HASH_FILE = DATA_DIR / ".pin_hash"

# Commission settings (DO NOT MODIFY)
COMMISSION_RATE = 0.04  # 4%

# Order settings
ORDER_EXPIRATION_MINUTES = 60  # Default order expiration time
LOW_STOCK_THRESHOLD = 5  # Alert when stock falls below this

# Currency conversion
DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]

# Monero settings
MONERO_CONFIRMATIONS_REQUIRED = 10  # Number of confirmations for payment
PAYMENT_CHECK_INTERVAL = 30  # Seconds between payment checks

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

# GUI settings
WINDOW_TITLE = "Signal Shop Bot - Seller Dashboard"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# API endpoints
XMR_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"

# Development mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
