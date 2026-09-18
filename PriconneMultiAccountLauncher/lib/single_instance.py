"""Single-instance guard via a named Win32 mutex.

Prevents two concurrent launcher processes from racing on the same
`data/` files / registry snapshots. Each subprocess mode
(game launcher, kill, force-user-game) is allowed to coexist with the
main GUI — they use a different mutex name suffix so the guard is
per-role, not strictly app-wide.
"""

import ctypes
import ctypes.wintypes as wintypes
import logging
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

ERROR_ALREADY_EXISTS = 183

WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
_kernel32.ReleaseMutex.restype = wintypes.BOOL

# One name for the whole machine-state critical section. Every process that
# mutates the shared Cygames subtree waits on this, whatever its role.
REGISTRY_SWAP_MUTEX = "Local\\PriconneMultiAccountLauncher.registry-swap"
_SWAP_TIMEOUT_MS = 120_000


class RegistrySwapBusy(Exception):
    """Another launcher process held the swap lock for too long."""


@contextmanager
def registry_swap_lock(timeout_ms: int = _SWAP_TIMEOUT_MS) -> Iterator[None]:
    """Serialize every mutation of the shared Cygames registry subtree.

    `SingleInstanceLock` above is per-ROLE and try-acquire, so two shortcut
    launches for different accounts run concurrently and can interleave
    backup/delete/import against the same subtree. The outcome is one account's
    binding written under another's slot — the exact cross-account contamination
    anti-detection.md A6 exists to prevent, and a plausible ban signal.

    This is a real cross-process mutex, taken for the whole swap and released in
    a finally. A blocked caller waits rather than racing.
    """
    handle = _kernel32.CreateMutexW(None, False, REGISTRY_SWAP_MUTEX)
    if not handle:
        err = ctypes.get_last_error()
        raise RegistrySwapBusy(f"CreateMutexW failed for the registry swap lock (err={err})")
    try:
        result = _kernel32.WaitForSingleObject(handle, timeout_ms)
        if result == WAIT_TIMEOUT:
            raise RegistrySwapBusy(
                "Another launcher instance has been switching accounts for over "
                f"{timeout_ms // 1000}s. Nothing was changed — close the other launcher and try again."
            )
        if result == WAIT_FAILED:
            err = ctypes.get_last_error()
            raise RegistrySwapBusy(f"Waiting for the registry swap lock failed (err={err})")
        if result == WAIT_ABANDONED:
            # Previous owner died mid-swap. We now own the mutex; the restore path
            # is transactional and the stale-baseline probe handles the leftovers.
            logger.warning("Registry swap lock was abandoned by a dead process — recovering.")
        try:
            yield
        finally:
            if not _kernel32.ReleaseMutex(handle):
                logger.error("ReleaseMutex failed for the registry swap lock (err=%d)", ctypes.get_last_error())
    finally:
        _kernel32.CloseHandle(handle)


class SingleInstanceLock:
    """Holds a Win32 named mutex for the lifetime of the launcher process.

    `is_owner` is False when another process already owns the mutex —
    callers should exit gracefully in that case.
    """

    def __init__(self, name: str) -> None:
        self._name = f"Local\\PriconneMultiAccountLauncher.{name}"
        self._handle: Optional[int] = None
        self.is_owner: bool = False

    def acquire(self) -> bool:
        handle = _kernel32.CreateMutexW(None, True, self._name)
        if not handle:
            err = ctypes.get_last_error()
            logger.error("CreateMutexW failed (err=%d) for %s", err, self._name)
            return False
        last_err = ctypes.get_last_error()
        self._handle = handle
        self.is_owner = last_err != ERROR_ALREADY_EXISTS
        if not self.is_owner:
            logger.warning("Another instance already holds mutex %s", self._name)
            # We still hold a handle — release it so the original owner remains sole.
            _kernel32.CloseHandle(handle)
            self._handle = None
        else:
            logger.info("Acquired single-instance mutex %s", self._name)
        return self.is_owner

    def release(self) -> None:
        if self._handle is not None:
            _kernel32.CloseHandle(self._handle)
            self._handle = None
            self.is_owner = False
