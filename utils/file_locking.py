#!/usr/bin/env python3
"""
Cross-Platform File Locking Utility

Provides file locking that works on Unix (fcntl) and Windows (msvcrt).
Raises RuntimeError on platforms without locking support to prevent
silent data corruption.
"""

import random
import time

# Cross-platform file locking imports
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class LockingNotSupportedError(RuntimeError):
    """Raised when file locking is not supported on the platform."""
    pass


def acquire_lock(fd, timeout: float = 30.0) -> None:
    """
    Acquire an exclusive lock on a file descriptor with a timeout.

    Args:
        fd: File object (must have fileno() method)
        timeout: Seconds to wait for the lock (default 30.0)

    Raises:
        LockingNotSupportedError: If file locking is not supported on this platform
        TimeoutError: If the lock cannot be acquired within the timeout

    Example:
        with open("myfile.lock", "w") as lock_fd:
            acquire_lock(lock_fd)
            # ... do work ...
            release_lock(lock_fd)

    Note:
        On Windows with msvcrt, locking works on text mode files but uses byte
        offsets. For maximum compatibility, consider opening in binary mode ("wb")
        when the lock file content is not meaningful. If text mode is used on
        Windows, newline translation may cause byte offset mismatches between
        lock/unlock operations, though this is unlikely to cause issues for
        the 1-byte semaphore pattern used here.
    """
    if not is_locking_supported():
        raise LockingNotSupportedError("File locking is not supported on this platform.")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if HAS_FCNTL:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            elif HAS_MSVCRT:
                fd.seek(0)
                # Lock 1 byte as a semaphore using non-blocking mode.
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                return
        except (IOError, OSError):
            # Lock is held by another process, wait and retry
            time.sleep(0.1 + random.uniform(0, 0.1))

    raise TimeoutError(f"Could not acquire lock on {fd.name} within {timeout} seconds.")


def release_lock(fd) -> None:
    """
    Release a lock on a file descriptor.

    Args:
        fd: File object (must have fileno() method)

    Raises:
        LockingNotSupportedError: If file locking is not supported on this platform

    Example:
        with open("myfile.lock", "w") as lock_fd:
            acquire_lock(lock_fd)
            # ... do work ...
            release_lock(lock_fd)
    """
    if HAS_FCNTL:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    elif HAS_MSVCRT:
        # Seek to same offset used in acquire_lock for unlock to work.
        fd.seek(0)
        # Unlock the 1 byte locked by acquire_lock.
        msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        raise LockingNotSupportedError("File locking is not supported on this platform.")


def is_locking_supported() -> bool:
    """
    Check if file locking is supported on this platform.

    Returns:
        True if fcntl or msvcrt is available, False otherwise
    """
    return HAS_FCNTL or HAS_MSVCRT
