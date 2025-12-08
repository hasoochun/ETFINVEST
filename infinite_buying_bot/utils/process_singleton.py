"""
Process singleton manager - ensures only one bot instance runs at a time
"""
import os
import sys
import signal
import logging
import psutil

logger = logging.getLogger(__name__)


class ProcessSingleton:
    """Ensures only one instance of the bot runs at a time using PID file"""
    
    def __init__(self, pid_file_path: str, process_name: str = "trading_bot"):
        """
        Initialize singleton manager
        
        Args:
            pid_file_path: Path to PID file (e.g., /tmp/trading_bot.pid)
            process_name: Name for logging purposes
        """
        self.pid_file = pid_file_path
        self.process_name = process_name
        self.current_pid = os.getpid()
        
    def acquire(self) -> bool:
        """
        Acquire singleton lock, killing previous instance if exists
        
        Returns:
            True if lock acquired successfully
        """
        # Check if PID file exists
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is still running
                if self._is_process_running(old_pid):
                    logger.warning(f"Found existing {self.process_name} instance (PID: {old_pid})")
                    
                    # Try to terminate gracefully first
                    if self._terminate_process(old_pid):
                        logger.info(f"Successfully terminated old instance (PID: {old_pid})")
                    else:
                        logger.error(f"Failed to terminate old instance (PID: {old_pid})")
                        return False
                else:
                    logger.info(f"Stale PID file found (PID: {old_pid} not running), cleaning up")
                    
            except (ValueError, IOError) as e:
                logger.warning(f"Error reading PID file: {e}, removing it")
                try:
                    os.remove(self.pid_file)
                except:
                    pass
        
        # Write current PID
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(self.current_pid))
            logger.info(f"{self.process_name} singleton acquired (PID: {self.current_pid})")
            return True
        except IOError as e:
            logger.error(f"Failed to write PID file: {e}")
            return False
    
    def release(self):
        """Release singleton lock by removing PID file"""
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    stored_pid = int(f.read().strip())
                
                # Only remove if it's our PID
                if stored_pid == self.current_pid:
                    os.remove(self.pid_file)
                    logger.info(f"{self.process_name} singleton released")
        except Exception as e:
            logger.warning(f"Error releasing singleton: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running"""
        try:
            process = psutil.Process(pid)
            # Check if it's actually our bot process
            cmdline = ' '.join(process.cmdline())
            return 'main_portfolio.py' in cmdline or 'infinite_buying_bot' in cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _terminate_process(self, pid: int, timeout: int = 10) -> bool:
        """
        Terminate process gracefully, force kill if needed
        
        Args:
            pid: Process ID to terminate
            timeout: Seconds to wait for graceful shutdown
            
        Returns:
            True if process terminated successfully
        """
        try:
            process = psutil.Process(pid)
            
            # Try SIGTERM first (graceful)
            logger.info(f"Sending SIGTERM to PID {pid}")
            process.terminate()
            
            # Wait for process to terminate
            try:
                process.wait(timeout=timeout)
                return True
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"Process {pid} didn't terminate gracefully, force killing")
                process.kill()
                process.wait(timeout=5)
                return True
                
        except psutil.NoSuchProcess:
            # Process already dead
            return True
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire {self.process_name} singleton lock")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
