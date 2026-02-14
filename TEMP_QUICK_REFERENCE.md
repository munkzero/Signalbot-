# Temp Directory Management - Quick Reference

## Quick Start

### Starting the Application
```bash
# Always use this (recommended)
./start.sh

# Not recommended (bypasses temp management)
python3 signalbot/main.py
```

### Checking Temp Directory
```bash
./check_temp.sh
```

### Stopping the Application
```bash
# Graceful shutdown (cleans up automatically)
Ctrl+C

# Or send termination signal
kill -TERM <pid>
```

## Common Tasks

### Check Current Usage
```bash
./check_temp.sh
```
Shows:
- Current size
- Number of libsignal directories
- Alerts if over 1GB

### Manual Cleanup (Emergency)
```bash
# Remove all libsignal directories
rm -rf ./tmp/libsignal*

# Remove entire tmp directory (nuclear option)
rm -rf ./tmp
```

### Check Disk Space
```bash
# Overall disk usage
df -h

# Temp directory size
du -sh ./tmp

# List libsignal directories
ls -lah ./tmp/libsignal*
```

## Troubleshooting

### "No space left on device"
1. Check temp usage: `./check_temp.sh`
2. Run cleanup: `./start.sh` (will clean before starting)
3. Manual cleanup: `rm -rf ./tmp/libsignal*`
4. Check overall space: `df -h`

### Too Many Orphaned Directories
- **Cause**: Application crashed multiple times
- **Solution**: `./start.sh` automatically cleans up
- **Prevention**: Fix underlying crashes

### Application Won't Start
1. Check TMPDIR is set: `echo $TMPDIR`
2. Check permissions: `ls -la ./tmp`
3. Create manually: `mkdir -p ./tmp`
4. Try without custom TMPDIR:
   ```bash
   unset TMPDIR
   unset JAVA_TOOL_OPTIONS
   python3 signalbot/main.py
   ```

## Understanding the Output

### start.sh Output
```
=========================================
Signal Shop Bot - Starting
=========================================
Cleaning up orphaned temp files...
✓ Cleaned up 2 orphaned libsignal directories

Temp directory: /path/to/tmp
Current usage: 127M
Active libsignal directories: 1
=========================================
```
- Shows cleanup results
- Displays current usage
- Lists active directories

### check_temp.sh Output (OK)
```
✓ Status: OK (under threshold)
```
- Everything is fine
- Usage under 1GB

### check_temp.sh Output (Warning)
```
⚠️  WARNING: Usage exceeds threshold!
Status: ALERT

Orphaned directories (older than 1 day):
...
```
- Action needed
- Run `./start.sh` to clean up

## What Gets Cleaned?

### Startup Cleanup (start.sh)
- **Removes**: libsignal* directories older than 1 day
- **Keeps**: Recent directories (<1 day old)
- **Keeps**: All non-libsignal files/directories

### Shutdown Cleanup (Ctrl+C)
- **Removes**: All libsignal* directories
- **Keeps**: Non-libsignal files/directories

### What's Safe?
- The tmp directory only contains Signal-cli temp files
- Safe to delete entire `./tmp` directory when app is NOT running
- Only libsignal* directories are touched by cleanup

## Expected Disk Usage

| Scenario | Size | Notes |
|----------|------|-------|
| Normal | ~127MB | One active process |
| After crash | ~254MB | Old + new directory |
| With 10 crashes (no cleanup) | ~1.3GB | Would trigger alert |
| With auto-cleanup | <254MB | Max 2 days of directories |

## Scripts Location

All scripts are in the project root:
- `./start.sh` - Startup with temp management
- `./check_temp.sh` - Monitor temp directory
- `./tmp/` - Project-local temp directory

## Documentation

- **Quick Reference**: This file
- **Full Guide**: See `TEMP_DIRECTORY_MANAGEMENT.md`
- **Implementation**: See `IMPLEMENTATION_COMPLETE_TEMP_MANAGEMENT.md`
- **Main Docs**: See `README.md`

## Tips

1. **Always use start.sh** for launching the application
2. **Run check_temp.sh** periodically to monitor usage
3. **Use Ctrl+C** to stop (not kill -9) for automatic cleanup
4. **Fix crashes** if you see many orphaned directories
5. **Check logs** if temp directory keeps growing

## Support

If you encounter issues:
1. Run `./check_temp.sh` to see current state
2. Check `TEMP_DIRECTORY_MANAGEMENT.md` for detailed troubleshooting
3. Report issues with output from check_temp.sh
