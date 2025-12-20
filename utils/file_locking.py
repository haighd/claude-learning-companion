#!/usr/bin/env python3
"""
Cross-Platform File Locking Utility

Provides file locking that works on Unix (fcntl) and Windows (msvcrt).
Raises RuntimeError on platforms without locking support to prevent
silent data corruption.
"""

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


def acquire_lock(fd) -> None:
    """
    Acquire an exclusive lock on a file descriptor.

    Args:
        fd: File object (must have fileno() method)

    Raises:
        RuntimeError: If file locking is not supported on this platform

    Example:
        with open("myfile.lock", "w") as lock_fd:
            acquire_lock(lock_fd)
            # ... do work ...
            release_lock(lock_fd)
    """
    if HAS_FCNTL:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
    elif HAS_MSVCRT:
        # msvcrt.locking: 3rd arg is number of bytes to lock.
        # We lock 1 byte as a semaphore - the lock file content doesn't matter.
        msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
    else:
        raise RuntimeError("File locking is not supported on this platform.")


def release_lock(fd) -> None:
    """
    Release a lock on a file descriptor.

    Args:
        fd: File object (must have fileno() method)

    Raises:
        RuntimeError: If file locking is not supported on this platform

    Example:
        with open("myfile.lock", "w") as lock_fd:
            acquire_lock(lock_fd)
            # ... do work ...
            release_lock(lock_fd)
    """
    if HAS_FCNTL:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    elif HAS_MSVCRT:
        # msvcrt.locking: 3rd arg is bytes to unlock (must match acquire_lock).
        msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        raise RuntimeError("File locking is not supported on this platform.")


def is_locking_supported() -> bool:
    """
    Check if file locking is supported on this platform.

    Returns:
        True if fcntl or msvcrt is available, False otherwise
    """
    return HAS_FCNTL or HAS_MSVCRT
