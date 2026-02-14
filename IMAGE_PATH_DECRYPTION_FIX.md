# Image Path Decryption Fix - Summary

## Problem

Image paths stored **encrypted** in the database were being used **directly** in catalog sending functions, causing file existence checks to fail because the code was looking for files with encrypted names instead of actual file paths.

### Evidence of the Bug

The `base64` module was imported **at the end** of `/signalbot/database/db.py` (line 184):

```python
class DatabaseManager:
    # ...
    def encrypt_field(self, value: str, salt: Optional[str] = None) -> tuple[str, str]:
        # ...
        None if salt is None else base64.b64decode(salt)  # Line 157 - base64 NOT YET IMPORTED!
        # ...

# Import base64 for decrypt_field  <-- Line 184 (WRONG LOCATION!)
import base64
```

This caused `encrypt_field()` to fail when trying to use `base64.b64decode()` before the module was imported.

## Solution

### 1. Fixed Import Order (`signalbot/database/db.py`)

**Before:**
```python
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import json
from ..config.settings import DATABASE_FILE
from ..core.security import security_manager

# ... 170+ lines of code ...

# Import base64 for decrypt_field
import base64  # Line 184 - TOO LATE!
```

**After:**
```python
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import json
import base64  # ✅ Now imported with other modules!
from ..config.settings import DATABASE_FILE
from ..core.security import security_manager
```

### 2. Improved Error Handling (`signalbot/models/product.py`)

**Before:**
```python
try:
    image_path = db_manager.decrypt_field(
        db_product.image_path,
        db_product.image_path_salt
    )
except:  # Silent failure - no logging!
    image_path = None
```

**After:**
```python
try:
    image_path = db_manager.decrypt_field(
        db_product.image_path,
        db_product.image_path_salt
    )
except Exception as e:
    print(f"ERROR: Failed to decrypt image path for product {db_product.product_id}: {e}")
    print(f"  Encrypted value: {db_product.image_path[:50] if db_product.image_path else 'None'}...")
    image_path = None
```

### 3. Enhanced Debug Logging (`buyer_handler.py` and `dashboard.py`)

**Before:**
```python
if product.image_path and os.path.exists(product.image_path):
    attachments.append(product.image_path)
```

**After:**
```python
if product.image_path:
    print(f"DEBUG: Product {product.name} has image_path: {product.image_path}")
    if os.path.exists(product.image_path):
        attachments.append(product.image_path)
        print(f"DEBUG: Attaching image for {product.name}: {product.image_path}")
    else:
        print(f"WARNING: Image path set but file missing for {product.name}: {product.image_path}")
        if not os.path.isabs(product.image_path):
            print(f"  Note: Path is relative, not absolute")
        print(f"  Current working directory: {os.getcwd()}")
```

## How It Works Now

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. STORING PRODUCT (Product.to_db_model)                    │
├─────────────────────────────────────────────────────────────┤
│ Plain text path:                                            │
│   /home/user/data/products/images/product.jpg               │
│                    ↓                                         │
│ encrypt_field() ✅ (base64 now imported!)                   │
│                    ↓                                         │
│ Database stores:                                            │
│   image_path: "oayaB4Obh4VSKGw7ZJNaZ..." (encrypted)        │
│   image_path_salt: "18q58GSP2/fJQLWRz..." (for decryption) │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. LOADING PRODUCT (Product.from_db_model)                  │
├─────────────────────────────────────────────────────────────┤
│ Database values:                                            │
│   image_path: "oayaB4Obh4VSKGw7ZJNaZ..." (encrypted)        │
│   image_path_salt: "18q58GSP2/fJQLWRz..."                  │
│                    ↓                                         │
│ decrypt_field() ✅ (properly decrypts)                      │
│                    ↓                                         │
│ Product object has:                                         │
│   image_path: "/home/user/data/products/images/product.jpg" │
│                (decrypted, usable path!)                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 3. SENDING CATALOG (buyer_handler.py / dashboard.py)       │
├─────────────────────────────────────────────────────────────┤
│ products = list_products(active_only=True)                  │
│   └─> Returns Product objects with DECRYPTED image_path ✅  │
│                    ↓                                         │
│ for product in products:                                    │
│   if os.path.exists(product.image_path):  # ✅ Checks real path│
│     attachments.append(product.image_path) # ✅ Sends real file│
└─────────────────────────────────────────────────────────────┘
```

## Test Results

### Unit Tests (`test_image_decryption.py`)

✅ All tests pass:
- base64 imported in correct location (line 11, not 184)
- Error logging implemented with detailed messages
- Enhanced debug logging in buyer_handler.py
- Enhanced debug logging in dashboard.py
- Encryption/decryption round-trip works correctly

### Integration Tests (`test_product_integration.py`)

✅ Full workflow validated:
1. Product created with image path → ✅ Path encrypted in database
2. Product retrieved → ✅ Path decrypted correctly
3. `list_products()` called → ✅ Returns decrypted paths
4. Catalog sending simulated → ✅ Receives usable file paths

### Existing Tests

✅ `test_catalog_and_message_deletion.py` - All existing tests still pass

## Files Modified

1. ✅ `signalbot/database/db.py` - Fixed base64 import location
2. ✅ `signalbot/models/product.py` - Enhanced error logging
3. ✅ `signalbot/core/buyer_handler.py` - Enhanced debug logging
4. ✅ `signalbot/gui/dashboard.py` - Enhanced debug logging
5. ✅ `test_image_decryption.py` - New unit tests
6. ✅ `test_product_integration.py` - New integration tests

## Impact

### Before Fix
- ❌ Image paths failed to encrypt/decrypt due to import order bug
- ❌ Catalog sending couldn't find image files
- ❌ Errors were silently caught without logging
- ❌ Debugging was difficult

### After Fix
- ✅ Image paths properly encrypted when stored
- ✅ Image paths properly decrypted when retrieved
- ✅ Catalog sending receives correct file paths
- ✅ Errors are logged with detailed information
- ✅ Enhanced debug output for troubleshooting
- ✅ Comprehensive test coverage

## Expected Output

When sending a catalog, you should now see:

```
DEBUG: Product smiles has image_path: /home/user/Desktop/Signalbot-/data/products/images/smiles.jpg
DEBUG: Attaching image for smiles: /home/user/Desktop/Signalbot-/data/products/images/smiles.jpg
DEBUG: Product cactus has image_path: /home/user/Desktop/Signalbot-/data/products/images/cactus.jpg
DEBUG: Attaching image for cactus: /home/user/Desktop/Signalbot-/data/products/images/cactus.jpg
```

Instead of:

```
WARNING: Image path set but file missing: aWl/uK+juwVUnruGVXdJ06K+GoUkCsMaoB1rTq+V4vE=
WARNING: Image path set but file missing: 7DbAT5tyM0DviFF9WBJMTUAZepRDYgix+qdFHPBwdmM=
```
