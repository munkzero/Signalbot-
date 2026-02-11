# Testing Guide for Critical Bug Fixes

This guide helps verify that all critical bug fixes are working correctly.

## Prerequisites
- signal-cli installed and configured
- Python 3.8+ with all dependencies from requirements.txt
- A test Signal account for buyer simulation

## Test 1: Message Receiving ✅

**What was fixed:**
- Disabled broken daemon mode (auto_daemon=False by default)
- Auto-start listening thread on dashboard init
- Added comprehensive debug logging

**How to test:**
1. Start the bot dashboard
2. Look for console output: `DEBUG: Dashboard initializing - starting message listener`
3. Look for: `DEBUG: start_listening() called for +YOURPHONE`
4. Look for: `DEBUG: Listen thread started successfully`
5. Look for: `DEBUG: Listen loop active for +YOURPHONE`
6. From another Signal account, send a message: "catalog"
7. Look for console output:
   ```
   DEBUG: Checking for messages...
   DEBUG: Received data from signal-cli
   DEBUG: Received message from +1234567890: catalog
   DEBUG: Passing message to buyer handler
   DEBUG: Processing buyer command: catalog
   DEBUG: Sending catalog to +1234567890
   ```

**Expected Result:**
- Bot should receive and process the message
- Catalog should be sent back to buyer
- All DEBUG messages should appear in console

**If it fails:**
- Check signal-cli is working: `signal-cli -u +YOURPHONE receive --json`
- Ensure phone number is configured correctly in database
- Check console for ERROR messages

---

## Test 2: Product Images Sending ✅

**What was fixed:**
- Added file existence checks before attaching images
- Added warning logs when image path is set but file missing

**How to test:**
1. Add a product with an image in the dashboard
2. Send "catalog" command from buyer account
3. Verify image is received with product info

**Test with missing image:**
1. Manually edit database to set image_path to non-existent file
2. Send "catalog" command
3. Look for console output: `WARNING: Image path set but file missing for ProductName: /path/to/missing.jpg`
4. Product info should still be sent (without image)

**Expected Result:**
- Products with valid images: image attached
- Products with missing images: warning logged, message sent without image
- No crashes or errors

---

## Test 3: View-Only Wallet Handling ✅

**What was fixed:**
- Added is_view_only() method to detect view-only wallets
- Skip commission sending for view-only wallets
- Log commission amount for manual payout

**How to test (if using view-only wallet):**
1. Configure bot with view-only wallet (address + view key only)
2. Create a test order
3. Simulate payment detection (or wait for real payment)
4. Look for console output:
   ```
   INFO: View-only wallet detected - Commission 0.007000 XMR for order 123 must be paid manually
   INFO: Send 0.007000 XMR to: 4...commission_address
   ```
5. Order should be marked as paid successfully
6. No crash or error when trying to send commission

**Expected Result:**
- Bot detects view-only wallet
- Commission amount logged for manual payment
- Order processing continues normally
- No transfer attempted

---

## Test 4: Payment Monitoring Auto-Start ✅

**What was fixed:**
- Auto-start payment monitoring when dashboard opens
- Register callbacks for buyer/seller notifications
- Added debug logging in monitoring loop

**How to test:**
1. Start the dashboard with wallet configured
2. Look for console output: `DEBUG: Dashboard initializing - starting payment monitoring`
3. Look for: `DEBUG: Payment monitoring started`
4. Look for: `DEBUG: Payment monitor loop started`
5. Create a test order
6. Every 30 seconds, look for: `DEBUG: Checking 1 pending orders for payments`
7. Look for: `DEBUG: Checking payment for order #123`

**Test payment detection:**
1. When payment is detected, should see:
   ```
   DEBUG: Payment detected! 0.150000 XMR for order #123
   ```
2. Buyer receives: `✅ Payment confirmed! Your order #123 is being processed.`
3. Seller receives: `💰 New paid order #123 - ProductName x2`

**Expected Result:**
- Payment monitoring starts automatically
- Checks for payments every 30 seconds
- Notifications sent when payment detected
- All DEBUG output appears

---

## Test 5: Buyer Command Variations ✅

**What was improved:**
- Case-insensitive matching
- More flexible keywords

**Commands to test:**
```
catalog       ✓ Should show products
catalogue     ✓ Should show products  
menu          ✓ Should show products
products      ✓ Should show products
items         ✓ Should show products
list          ✓ Should show products
show products ✓ Should show products
show catalog  ✓ Should show products
view products ✓ Should show products
CATALOG       ✓ Should work (case insensitive)

order #1 qty 2       ✓ Create order
buy #2 qty 5         ✓ Create order
ORDER #3 QTY 1       ✓ Case insensitive

help          ✓ Show help message
```

**Should NOT trigger catalog:**
```
show me your address   ✗ Should not show catalog
I don't want catalog   ✗ Should not show catalog
shower                 ✗ Should not show catalog
```

---

## Test 6: Error Handling ✅

**Test scenarios:**

1. **Order with insufficient stock:**
   - Order more than available
   - Should receive stock limitation message
   - No crash

2. **Invalid product ID:**
   - Send: "order #999 qty 1"
   - Should receive: "Product #999 not found"
   - No crash

3. **QR code generation fails:**
   - Order should still be created
   - Payment info sent without QR
   - Error logged in console

4. **Wallet RPC timeout:**
   - Disconnect wallet or node
   - Should see: `ERROR: Wallet RPC timeout - check node connection`
   - Graceful error handling

---

## Test 7: Debug Output Verification ✅

**Check for these debug messages:**

**Signal Handler:**
- `DEBUG: SignalHandler initialized with phone_number=...`
- `DEBUG: start_listening() called for +...`
- `DEBUG: Listen loop active for +...`
- `DEBUG: Checking for messages...`
- `DEBUG: Received message from +...: ...`
- `DEBUG: Message sent successfully to +...`

**Buyer Handler:**
- `DEBUG: Processing buyer command: ...`
- `DEBUG: Sending catalog to +...`
- `DEBUG: Creating order for product #1 qty 2`
- `DEBUG: Order #123 created successfully`
- `DEBUG: QR code generated at /tmp/order_123_qr.png`

**Payment Processor:**
- `DEBUG: Payment monitoring started`
- `DEBUG: Payment monitor loop started`
- `DEBUG: Checking 3 pending orders for payments`
- `DEBUG: Checking payment for order #123`
- `DEBUG: Payment detected! 0.150000 XMR for order #123`

**Monero Wallet:**
- `WARNING: Cannot determine wallet type (assuming view-only): ...`
- `INFO: View-only wallet detected - Commission ... XMR must be paid manually`

---

## Common Issues & Solutions

### Issue: Bot not receiving messages
**Check:**
- Console shows `DEBUG: Listen loop active`?
- Run manually: `signal-cli -u +YOURPHONE receive --json`
- Phone number correct in database?

### Issue: Images not sending
**Check:**
- Console shows `WARNING: Image path set but file missing`?
- File path correct in database?
- File actually exists at that path?

### Issue: Payment monitoring not starting
**Check:**
- Wallet configured in database?
- Console shows `DEBUG: Payment monitoring started`?
- Any errors in `WARNING: Failed to initialize payment monitoring`?

### Issue: Commission sending fails
**Check:**
- Is it a view-only wallet? (Should see INFO message)
- Wallet has sufficient balance for fee?
- Node is synced?

---

## Expected Console Output (Healthy Bot)

```
DEBUG: SignalHandler initialized with phone_number=+1234567890, auto_daemon=False
DEBUG: Dashboard initializing - starting message listener
DEBUG: start_listening() called for +1234567890
DEBUG: Listen thread started successfully
DEBUG: Dashboard initializing - starting payment monitoring
DEBUG: Payment monitoring started
DEBUG: Payment monitor loop started
DEBUG: Listen loop active for +1234567890
DEBUG: Checking for messages...
DEBUG: Checking 0 pending orders for payments
DEBUG: Checking for messages...
```

When buyer sends "catalog":
```
DEBUG: Received data from signal-cli
DEBUG: Received message from +0987654321: catalog
DEBUG: Passing message to buyer handler
DEBUG: Processing buyer command: catalog
DEBUG: Sending catalog to +0987654321
DEBUG: Attaching image for Product1: /path/to/image.jpg
DEBUG: Message sent successfully to +0987654321
```

---

## Success Criteria

✅ All DEBUG messages appear in console
✅ Bot receives and processes buyer messages
✅ Catalog sends with images (when images exist)
✅ View-only wallet doesn't crash (logs commission)
✅ Payment monitoring runs automatically
✅ Notifications sent on payment detection
✅ Error messages are clear and helpful
✅ No crashes or unhandled exceptions

---

## Performance Expectations

- Message receiving: Every 2 seconds
- Payment checking: Every 30 seconds
- Message sending: 10-15 seconds per message
- Catalog sending: 1 second delay between products

---

## Security Notes

- All DEBUG output reviewed by CodeQL: ✅ No security alerts
- No sensitive data in logs (addresses truncated)
- Proper exception handling prevents data leaks
- View-only wallet safety: Cannot accidentally spend

---

## Questions or Issues?

If any test fails or you see unexpected behavior:
1. Check console output for ERROR/WARNING messages
2. Verify signal-cli is working independently
3. Check database configuration
4. Review this testing guide for similar scenarios
