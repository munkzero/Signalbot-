#!/usr/bin/env python3
"""
Integration test for RPC process management
Tests real scenarios with mock process management
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from signalbot.core.wallet_setup import WalletSetupManager


def test_scenario_1_clean_start():
    """Test Scenario 1: Clean start with no existing RPC"""
    print("\n" + "="*70)
    print("TEST SCENARIO 1: Clean start (no existing RPC)")
    print("="*70)
    
    # Create temp wallet directory
    with tempfile.TemporaryDirectory() as tmpdir:
        wallet_path = Path(tmpdir) / "test_wallet"
        
        # Create wallet files
        wallet_path.parent.mkdir(parents=True, exist_ok=True)
        Path(f"{wallet_path}.keys").touch()
        
        # Create manager
        manager = WalletSetupManager(
            wallet_path=str(wallet_path),
            daemon_address="localhost",
            daemon_port=18081,
            rpc_port=18083,
            password=""
        )
        
        # Mock subprocess and requests
        with patch('subprocess.run') as mock_run, \
             patch('subprocess.Popen') as mock_popen, \
             patch('requests.post') as mock_post:
            
            # lsof returns nothing (no process on port)
            mock_run.return_value = Mock(stdout="", returncode=1)
            
            # Popen returns a mock process
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None  # Process is alive
            mock_popen.return_value = mock_process
            
            # RPC becomes ready
            mock_post.return_value = Mock(status_code=200)
            
            # Start RPC
            result = manager.start_rpc()
            
            # Verify
            assert result == True, "start_rpc() should return True"
            assert manager.rpc_process == mock_process, "rpc_process should be set"
            assert manager.rpc_process.pid == 12345, "PID should match"
            
            print("✅ Clean start works correctly")
            print(f"  - RPC process started: PID {manager.rpc_process.pid}")
            print(f"  - Process handle set: {manager.rpc_process is not None}")
    
    return True


def test_scenario_2_orphaned_rpc():
    """Test Scenario 2: Orphaned RPC from previous run"""
    print("\n" + "="*70)
    print("TEST SCENARIO 2: Orphaned RPC from previous run")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        wallet_path = Path(tmpdir) / "test_wallet"
        Path(f"{wallet_path}.keys").touch()
        
        # Create PID file from "previous run"
        pid_file = Path(tmpdir) / ".rpc.pid"
        pid_file.write_text("99999")
        
        manager = WalletSetupManager(
            wallet_path=str(wallet_path),
            daemon_address="localhost",
            daemon_port=18081,
            rpc_port=18083,
            password=""
        )
        
        with patch('subprocess.run') as mock_run, \
             patch('subprocess.Popen') as mock_popen, \
             patch('requests.post') as mock_post, \
             patch('os.kill') as mock_kill, \
             patch('time.sleep'):
            
            # First call to lsof finds orphan
            # Second call after kill finds nothing
            mock_run.side_effect = [
                Mock(stdout="99999\n", returncode=0),  # lsof finds orphan
                Mock(stdout="", returncode=1),  # After kill, port is free
            ]
            
            # os.kill calls
            mock_kill.side_effect = [
                None,  # SIGTERM succeeds
                ProcessLookupError(),  # Check if alive - already dead
            ]
            
            # New process
            mock_process = Mock()
            mock_process.pid = 12346
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # RPC ready
            mock_post.return_value = Mock(status_code=200)
            
            # Start RPC
            result = manager.start_rpc()
            
            # Verify orphan was killed
            assert mock_kill.call_count >= 1, "Should have killed orphan"
            
            # Verify new process started
            assert result == True, "start_rpc() should succeed"
            assert manager.rpc_process.pid == 12346, "Should have new PID"
            
            print("✅ Orphan cleanup works correctly")
            print(f"  - Killed orphan PID: 99999")
            print(f"  - Started new RPC: PID {manager.rpc_process.pid}")
    
    return True


def test_scenario_3_double_start_prevention():
    """Test Scenario 3: Calling start_rpc twice"""
    print("\n" + "="*70)
    print("TEST SCENARIO 3: Double start prevention")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        wallet_path = Path(tmpdir) / "test_wallet"
        Path(f"{wallet_path}.keys").touch()
        
        manager = WalletSetupManager(
            wallet_path=str(wallet_path),
            daemon_address="localhost",
            daemon_port=18081,
            rpc_port=18083,
            password=""
        )
        
        with patch('subprocess.run') as mock_run, \
             patch('subprocess.Popen') as mock_popen, \
             patch('requests.post') as mock_post:
            
            # First start: no process on port
            mock_run.return_value = Mock(stdout="", returncode=1)
            
            mock_process = Mock()
            mock_process.pid = 12347
            mock_process.poll.return_value = None  # Process is alive
            mock_popen.return_value = mock_process
            
            mock_post.return_value = Mock(status_code=200)
            
            # First start succeeds
            result1 = manager.start_rpc()
            assert result1 == True
            first_pid = manager.rpc_process.pid
            
            # Reset mocks for second call
            mock_run.reset_mock()
            mock_popen.reset_mock()
            
            # Second start: our process is still alive
            # The new check at the beginning should detect this and return True immediately
            result2 = manager.start_rpc()
            
            # Should return True (already running under our control)
            assert result2 == True, "Second start should return True (already running)"
            assert manager.rpc_process.pid == first_pid, "Should keep same process"
            
            # Should NOT have called cleanup or started new process
            assert mock_run.call_count == 0, "Should not call lsof (early return)"
            assert mock_popen.call_count == 0, "Should not start new process"
            
            print("✅ Double start prevention works")
            print(f"  - First start: PID {first_pid}")
            print(f"  - Second start: Detected existing process, returned True")
            print(f"  - No unnecessary cleanup or restart")
    
    return True


def test_scenario_4_cleanup_on_shutdown():
    """Test Scenario 4: Cleanup via __del__"""
    print("\n" + "="*70)
    print("TEST SCENARIO 4: Cleanup on shutdown (__del__)")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        wallet_path = Path(tmpdir) / "test_wallet"
        Path(f"{wallet_path}.keys").touch()
        
        manager = WalletSetupManager(
            wallet_path=str(wallet_path),
            daemon_address="localhost",
            daemon_port=18081,
            rpc_port=18083,
            password=""
        )
        
        # Create mock process
        mock_process = Mock()
        mock_process.pid = 12348
        mock_process.poll.return_value = None  # Still alive
        manager.rpc_process = mock_process
        
        # Create PID file
        manager.rpc_pid_file = str(Path(tmpdir) / ".rpc.pid")
        Path(manager.rpc_pid_file).write_text("12348")
        
        with patch('subprocess.TimeoutExpired', subprocess.TimeoutExpired):
            # Call destructor
            manager.__del__()
            
            # Verify process was terminated
            assert mock_process.terminate.called, "Should call terminate()"
            assert mock_process.wait.called, "Should call wait()"
            
            # Verify PID file removed
            assert not Path(manager.rpc_pid_file).exists(), "PID file should be removed"
            
            print("✅ Cleanup on shutdown works")
            print(f"  - Process terminated: PID 12348")
            print(f"  - PID file removed")
    
    return True


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("RPC PROCESS MANAGEMENT - INTEGRATION TESTS")
    print("="*70)
    
    tests = [
        ("Clean Start", test_scenario_1_clean_start),
        ("Orphaned RPC Cleanup", test_scenario_2_orphaned_rpc),
        ("Double Start Prevention", test_scenario_3_double_start_prevention),
        ("Cleanup on Shutdown", test_scenario_4_cleanup_on_shutdown),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)
    
    return passed == total


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
