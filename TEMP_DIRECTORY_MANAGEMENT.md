# Temporary Directory Management

## Problem Overview

Signal-cli (used for Signal messenger integration) extracts native libraries to temporary directories on every startup. Each extraction creates approximately 127MB of files in directories named `libsignal*`.

### Impact

When the application crashes during startup or is force-killed, these temporary directories are **not automatically cleaned up**, leading to:

- **Disk space accumulation**: Each failed startup leaves 127MB of orphaned files
- **Cascading failures**: On systems with limited space (especially `/tmp` tmpfs partitions), the temp directory can fill up after 60+ failed attempts (~7.7GB)
- **Complete failure**: Once `/tmp` is full, signal-cli cannot start at all ("No space left on device")
- **Manual intervention required**: Without automated cleanup, users must manually delete orphaned directories

This is particularly problematic on systems with:
- Limited disk space (e.g., 70GB total)
- Small `/tmp` partitions (often tmpfs mounted with 2-8GB limits)
- Frequent crashes or restarts during development/debugging

## Solution

This project implements a **three-layer defense** against temp directory accumulation:

### 1. Custom Temp Directory (Prevention)

Instead of using the system `/tmp` directory, we use a **project-local temp directory**:

```bash
export TMPDIR=~/path/to/Signalbot-/tmp
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$TMPDIR"
```

**Benefits:**
- Isolates our temp files from system temp
- Easier to monitor and manage
- Won't interfere with other applications
- Can grow as needed (not limited by tmpfs size)

### 2. Automatic Cleanup on Startup

The `start.sh` script automatically cleans up orphaned directories older than 1 day **before** launching the application:

```bash
find "$TMPDIR" -name "libsignal*" -type d -mtime +1 -exec rm -rf {} +
```

**Benefits:**
- Runs before every startup
- Protects against accumulated orphaned directories
- Safe (only removes files older than 1 day)
- Non-intrusive (won't affect currently running processes)

### 3. Cleanup on Graceful Shutdown

The application now includes signal handlers (SIGINT/SIGTERM) that clean up temp files when shutting down gracefully:

```python
def cleanup_temp_files():
    """Clean up libsignal temp directories on graceful shutdown"""
    # Removes all libsignal* directories in TMPDIR
```

**Benefits:**
- Prevents accumulation from normal shutdowns
- Reduces disk space usage immediately
- Works with Ctrl+C and process termination

## Usage

### Starting the Application

**Always use the startup script** instead of running Python directly:

```bash
# Recommended way to start
./start.sh

# NOT recommended (bypasses temp management)
python3 signalbot/main.py
```

The startup script will:
1. Set up the custom temp directory
2. Clean up orphaned files older than 1 day
3. Show current temp directory usage
4. Activate the virtual environment
5. Launch the application

### Monitoring Temp Directory

Check temp directory status at any time:

```bash
./check_temp.sh
```

**Example output (healthy):**
```
=========================================
Temp Directory Monitor
=========================================

Location: /home/user/Signalbot-/tmp
Usage: 127M (127 MB)
Threshold: 1024 MB

libsignal directories:
  Total: 1
  Orphaned (>1 day): 0

✓ Status: OK (under threshold)
```

**Example output (warning):**
```
⚠️  WARNING: Usage exceeds threshold!
Status: ALERT

Orphaned directories (older than 1 day):
----------------------------------------
  /home/user/Signalbot-/tmp/libsignal_jni123456
    Size: 127M
    Modified: 2024-01-15 10:23:45
  /home/user/Signalbot-/tmp/libsignal_jni789012
    Size: 127M
    Modified: 2024-01-14 08:15:22

Recommended actions:
  1. Run start.sh to auto-cleanup orphaned directories
  2. Or manually cleanup: rm -rf /home/user/Signalbot-/tmp/libsignal*
  3. Consider increasing available disk space
```

### Manual Cleanup (if needed)

If you need to manually clean up temp files:

```bash
# Remove all libsignal directories
rm -rf ~/path/to/Signalbot-/tmp/libsignal*

# Or remove the entire temp directory
rm -rf ~/path/to/Signalbot-/tmp
```

**Note:** Only do this when the application is NOT running.

## Technical Details

### Temp Directory Location

The temp directory is located at `./tmp` in the project root (next to `start.sh`).

**Path resolution:**
- Startup script: `$SCRIPT_DIR/tmp` (automatically detected)
- Python application: Uses `$TMPDIR` environment variable

### Cleanup Criteria

**Startup cleanup:**
- Only removes directories matching `libsignal*`
- Only removes directories older than 1 day (`-mtime +1`)
- Safe to run even if process is running (active directories are recent)

**Shutdown cleanup:**
- Removes all `libsignal*` directories (regardless of age)
- Only runs on graceful shutdown (SIGINT/SIGTERM)
- Does not run on crashes or SIGKILL

### Typical Disk Usage

| Scenario | Disk Usage | Notes |
|----------|------------|-------|
| Normal operation | ~127MB | One active libsignal directory |
| After crash (before cleanup) | ~254MB | Old + new directory |
| After 10 crashes (no cleanup) | ~1.27GB | 10 orphaned directories |
| After 60 crashes (no cleanup) | ~7.6GB | Can fill small /tmp partitions |
| With auto-cleanup enabled | ~127-254MB | Maximum 2 directories (current + previous day) |

### Why 1 Day Threshold?

The 1-day threshold for startup cleanup ensures:
- **Safety**: Won't interfere with recently created directories
- **Effectiveness**: Catches orphaned directories from crashes
- **Balance**: Aggressive enough to prevent accumulation, conservative enough to avoid accidents

Active signal-cli processes create new temp directories, so a 1-day-old directory is definitely orphaned.

## Troubleshooting

### "No space left on device" error

**Symptoms:**
```
Error: java.io.IOException: No space left on device
```

**Cause:** The temp directory (or partition) is full.

**Solutions:**
1. Run `./check_temp.sh` to see usage
2. Run `./start.sh` to auto-cleanup (recommended)
3. Manually remove orphaned directories:
   ```bash
   find ./tmp -name "libsignal*" -type d -mtime +1 -exec rm -rf {} +
   ```
4. Check overall disk space: `df -h`

### Temp directory still growing

**If the temp directory continues to grow despite using `start.sh`:**

1. **Check for crashes during startup:**
   - Look for errors in logs
   - Fix underlying issues causing crashes
   - Each crash leaves a 127MB directory

2. **Verify TMPDIR is set:**
   ```bash
   echo $TMPDIR
   # Should show: /path/to/Signalbot-/tmp
   ```

3. **Check if using start.sh:**
   - Always use `./start.sh` to launch
   - Don't run `python3 signalbot/main.py` directly

4. **Verify cleanup is running:**
   - Check start.sh output for cleanup messages
   - Look for "Cleaned up X orphaned libsignal directories"

### Application won't start

**If the application fails to start after temp management changes:**

1. **Check TMPDIR permissions:**
   ```bash
   ls -la ./tmp
   # Should be readable/writable by your user
   ```

2. **Create temp directory manually:**
   ```bash
   mkdir -p ./tmp
   chmod 755 ./tmp
   ```

3. **Check Java options:**
   ```bash
   echo $JAVA_TOOL_OPTIONS
   # Should include: -Djava.io.tmpdir=/path/to/tmp
   ```

4. **Try without custom TMPDIR:**
   ```bash
   unset TMPDIR
   unset JAVA_TOOL_OPTIONS
   python3 signalbot/main.py
   ```

## Best Practices

1. **Always use start.sh**: This ensures temp management is active
2. **Monitor regularly**: Run `check_temp.sh` periodically to catch issues
3. **Watch for crashes**: If the app crashes frequently, investigate and fix the root cause
4. **Graceful shutdowns**: Use Ctrl+C instead of `kill -9` when possible
5. **Sufficient disk space**: Ensure at least 1-2GB free space for temp files

## System Requirements

The temp management solution works on:
- **Linux**: Tested and fully supported
- **macOS**: Should work (uses standard Unix commands)
- **Windows**: Requires WSL or Git Bash (not tested with Windows native)

**Required commands:**
- `find` (with `-mtime` support)
- `du` (disk usage)
- `rm` (recursive removal)
- `bash` (for shell scripts)

## Migration Guide

### From Old Setup (Using /tmp)

If you were previously running without temp management:

1. **Clean up existing /tmp files:**
   ```bash
   # Check what's there
   ls -la /tmp/libsignal*
   
   # Remove if safe (no processes using them)
   rm -rf /tmp/libsignal*
   ```

2. **Start using the new script:**
   ```bash
   ./start.sh
   ```

3. **Verify new temp location:**
   ```bash
   ./check_temp.sh
   ```

The application will now use `./tmp` instead of `/tmp`.

### From Manual TMPDIR Setup

If you were already using a custom TMPDIR:

1. **Remove old TMPDIR settings** from your shell profile (.bashrc, etc.)
2. **Use start.sh** which sets TMPDIR automatically
3. **Update any scripts** that launch the application to use start.sh

## Future Improvements

Potential enhancements for temp directory management:

1. **Configurable cleanup threshold**: Allow users to set custom age threshold
2. **Size-based cleanup**: Clean up if total usage exceeds threshold
3. **Automatic monitoring**: Background process that monitors and alerts
4. **Systemd integration**: Service file with proper temp directory handling
5. **Windows support**: PowerShell equivalent of bash scripts

## Contributing

If you experience temp directory issues not covered here:

1. Check the current temp directory usage
2. Review application logs for errors
3. Document the issue with specifics (disk space, number of orphans, etc.)
4. Submit an issue with reproduction steps

## References

- [Signal-CLI GitHub](https://github.com/AsamK/signal-cli)
- [Java temp directory documentation](https://docs.oracle.com/javase/8/docs/api/java/io/tmpdir.html)
- [tmpfs on Linux](https://www.kernel.org/doc/html/latest/filesystems/tmpfs.html)
