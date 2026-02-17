#!/bin/bash
# SignalBot Debug Report Generator
# Collects comprehensive diagnostic information for debugging

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for terminal output (optional)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Header
echo "========================================"
echo "SignalBot Debug Report"
echo "Generated: $(date)"
echo "========================================"
echo ""

# 1. System Information
echo "## SYSTEM INFORMATION"
echo "OS: $(uname -a)"
echo "Python: $(python3 --version 2>&1)"
echo "Java: $(java -version 2>&1 | head -1)"
echo "Monero RPC: $(which monero-wallet-rpc 2>/dev/null && monero-wallet-rpc --version 2>&1 | head -1 || echo 'NOT FOUND')"
echo "Signal-CLI: $(which signal-cli 2>/dev/null && signal-cli --version 2>&1 || echo 'NOT FOUND')"
echo ""

# 2. Running Processes
echo "## RUNNING PROCESSES"
echo "Python processes:"
ps aux | grep -E "python|signalbot" | grep -v grep || echo "None found"
echo ""
echo "Monero processes:"
ps aux | grep -E "monero" | grep -v grep || echo "None found"
echo ""
echo "Signal processes:"
ps aux | grep -E "signal-cli" | grep -v grep || echo "None found"
echo ""
echo "Cleanup daemon:"
if [ -f "$SCRIPT_DIR/cleanup_daemon.pid" ]; then
    PID=$(cat "$SCRIPT_DIR/cleanup_daemon.pid" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "✓ Running (PID: $PID)"
        ps aux | grep "$PID" | grep -v grep || echo "Process details not available"
    else
        echo "✗ Not running (stale PID file)"
    fi
else
    echo "Not running (no PID file)"
fi
echo ""

# 3. Port Status
echo "## PORT STATUS"
echo "Port 18083 (Monero RPC):"
if command -v lsof &> /dev/null; then
    lsof -i :18083 2>/dev/null || echo "Not in use (lsof)"
else
    echo "lsof not available"
fi
if command -v netstat &> /dev/null; then
    netstat -tlnp 2>/dev/null | grep 18083 || echo "Not listening (netstat)"
elif command -v ss &> /dev/null; then
    ss -tlnp 2>/dev/null | grep 18083 || echo "Not listening (ss)"
else
    echo "netstat/ss not available"
fi
echo ""

# 4. File Status
echo "## FILE STATUS"
echo "Current directory: $SCRIPT_DIR"
echo ""
echo "Wallet directory:"
if [ -d "$SCRIPT_DIR/data/wallet/" ]; then
    ls -lh "$SCRIPT_DIR/data/wallet/" 2>/dev/null || echo "Cannot list directory"
else
    echo "Directory not found: $SCRIPT_DIR/data/wallet/"
fi
echo ""
echo "Data directory:"
if [ -d "$SCRIPT_DIR/data/" ]; then
    find "$SCRIPT_DIR/data/" -type f -name "*.keys" -o -name "*.db" -o -name "wallet*" 2>/dev/null | while read -r file; do
        ls -lh "$file" 2>/dev/null
    done || echo "No data files found"
else
    echo "Directory not found: $SCRIPT_DIR/data/"
fi
echo ""
echo "Log files:"
if [ -d "$SCRIPT_DIR/logs/" ]; then
    find "$SCRIPT_DIR/logs/" -name "*.log" -type f -exec ls -lh {} \; 2>/dev/null || echo "No logs in logs/"
else
    echo "logs/ directory not found"
fi
find "$SCRIPT_DIR" -maxdepth 2 -name "*.log" -type f -exec ls -lh {} \; 2>/dev/null || echo "No .log files found"
echo ""
echo "Temp directory:"
if [ -d "$SCRIPT_DIR/tmp/" ]; then
    USAGE=$(du -sh "$SCRIPT_DIR/tmp/" 2>/dev/null | cut -f1)
    LIBSIGNAL_COUNT=$(find "$SCRIPT_DIR/tmp/" -maxdepth 1 -name "libsignal*" -type d 2>/dev/null | wc -l)
    echo "Usage: $USAGE"
    echo "Libsignal directories: $LIBSIGNAL_COUNT"
else
    echo "tmp/ directory not found"
fi
echo ""

# 5. Log Contents (last 100 lines each)
echo "## LOG CONTENTS"
echo ""

echo "### Monero RPC Log (last 100 lines)"
if [ -f "$SCRIPT_DIR/data/wallet/monero-wallet-rpc.log" ]; then
    tail -100 "$SCRIPT_DIR/data/wallet/monero-wallet-rpc.log" 2>/dev/null || echo "Cannot read log file"
else
    echo "Log file not found: $SCRIPT_DIR/data/wallet/monero-wallet-rpc.log"
fi
echo ""

echo "### Monero CLI Log (last 100 lines)"
if [ -f "$SCRIPT_DIR/data/wallet/monero-wallet-cli.log" ]; then
    tail -100 "$SCRIPT_DIR/data/wallet/monero-wallet-cli.log" 2>/dev/null || echo "Cannot read log file"
else
    echo "Log file not found: $SCRIPT_DIR/data/wallet/monero-wallet-cli.log"
fi
echo ""

echo "### Cleanup Daemon Log (last 100 lines)"
if [ -f "$SCRIPT_DIR/logs/cleanup.log" ]; then
    tail -100 "$SCRIPT_DIR/logs/cleanup.log" 2>/dev/null || echo "Cannot read log file"
else
    echo "Log file not found: $SCRIPT_DIR/logs/cleanup.log"
fi
echo ""

echo "### Other Log Files"
find "$SCRIPT_DIR" -maxdepth 2 -name "*.log" -type f ! -path "*/data/wallet/*" ! -path "*/logs/cleanup.log" 2>/dev/null | while read -r logfile; do
    echo "#### $logfile (last 50 lines)"
    tail -50 "$logfile" 2>/dev/null || echo "Cannot read log file"
    echo ""
done
echo ""

# 6. Connectivity Tests
echo "## CONNECTIVITY TESTS"
echo ""
echo "Testing Monero node (xmr-node.cakewallet.com:18081)..."
if command -v curl &> /dev/null; then
    if curl -s -m 5 -X POST xmr-node.cakewallet.com:18081/json_rpc \
      -d '{"jsonrpc":"2.0","id":"0","method":"get_height"}' \
      -H 'Content-Type: application/json' 2>&1 | grep -q "result"; then
        echo "✓ Node reachable"
    else
        echo "✗ Node unreachable or not responding"
    fi
else
    echo "curl not available - cannot test connectivity"
fi
echo ""

echo "Testing RPC (localhost:18083)..."
if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -m 2 -X POST http://127.0.0.1:18083/json_rpc \
      -d '{"jsonrpc":"2.0","id":"0","method":"get_balance"}' \
      -H 'Content-Type: application/json' 2>&1)
    if echo "$RESPONSE" | grep -q "result\|error"; then
        echo "✓ RPC responding"
        echo "Response: $RESPONSE" | head -c 200
    else
        echo "✗ RPC not responding"
        echo "Response: $RESPONSE" | head -c 200
    fi
else
    echo "curl not available - cannot test RPC"
fi
echo ""

echo "Signal-CLI status:"
if command -v signal-cli &> /dev/null; then
    echo "Available accounts:"
    signal-cli listAccounts 2>/dev/null || echo "Cannot list accounts"
else
    echo "signal-cli not found"
fi
echo ""

# 7. Recent Errors
echo "## RECENT ERRORS (last 20)"
echo ""
ERROR_COUNT=$(find "$SCRIPT_DIR" -name "*.log" -type f -exec grep -i -E "error|fail|exception" {} + 2>/dev/null | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "Found $ERROR_COUNT error entries total. Showing last 20:"
    find "$SCRIPT_DIR" -name "*.log" -type f -exec grep -i -E "error|fail|exception" {} + 2>/dev/null | tail -20
else
    echo "No errors found in log files"
fi
echo ""

# 8. Environment Check
echo "## ENVIRONMENT CHECK"
echo ""
echo "Current directory: $(pwd)"
echo "Script directory: $SCRIPT_DIR"
echo "User: $(whoami)"
echo ""
echo "Virtual environment: ${VIRTUAL_ENV:-Not activated}"
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "✓ venv/ exists"
elif [ -d "$SCRIPT_DIR/env" ]; then
    echo "✓ env/ exists"
else
    echo "✗ No virtual environment directory found"
fi
echo ""
echo "Config file (.env): $([ -f "$SCRIPT_DIR/.env" ] && echo 'Yes' || echo 'No')"
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "  Size: $(ls -lh "$SCRIPT_DIR/.env" 2>/dev/null | awk '{print $5}')"
fi
echo ""
echo "Python packages:"
if command -v pip &> /dev/null; then
    pip list 2>/dev/null | grep -E "monero|requests|signal|pyqt" || echo "None of the expected packages found"
else
    echo "pip not available"
fi
echo ""
echo "Requirements file:"
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "✓ requirements.txt exists"
    wc -l "$SCRIPT_DIR/requirements.txt" 2>/dev/null
else
    echo "✗ requirements.txt not found"
fi
echo ""

# 9. Detected Issues Summary
echo "## DETECTED ISSUES"
echo ""

ISSUES_FOUND=0

# Check for common issues
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "✗ Missing .env file"
    ((ISSUES_FOUND++))
fi

if ! command -v python3 &> /dev/null; then
    echo "✗ Python3 not found"
    ((ISSUES_FOUND++))
fi

if ! command -v signal-cli &> /dev/null; then
    echo "✗ signal-cli not installed"
    ((ISSUES_FOUND++))
fi

if ! command -v monero-wallet-rpc &> /dev/null; then
    echo "✗ monero-wallet-rpc not installed"
    ((ISSUES_FOUND++))
fi

if [ ! -d "$SCRIPT_DIR/venv" ] && [ ! -d "$SCRIPT_DIR/env" ]; then
    echo "⚠ No virtual environment found"
    ((ISSUES_FOUND++))
fi

if [ "$ERROR_COUNT" -gt 50 ]; then
    echo "⚠ High error count in logs ($ERROR_COUNT errors)"
    ((ISSUES_FOUND++))
fi

if [ ! -d "$SCRIPT_DIR/data" ]; then
    echo "⚠ data/ directory not found"
    ((ISSUES_FOUND++))
fi

if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo "✓ No obvious issues detected"
else
    echo ""
    echo "Total issues detected: $ISSUES_FOUND"
fi
echo ""

# 10. Summary
echo "========================================"
echo "DEBUG REPORT COMPLETE"
echo "========================================"
echo ""
echo "To share this report:"
echo "1. Run: ./debug-report.sh > debug-report.txt"
echo "2. Or copy ALL output above"
echo "3. Paste into GitHub issue or chat"
echo "4. Do NOT edit or truncate"
echo ""
echo "Privacy notice:"
echo "- This report may contain wallet addresses"
echo "- Review before sharing publicly"
echo "- Redact sensitive information if needed"
echo ""
