"""Single-instance guard via a named Win32 mutex.

Prevents two concurrent launcher processes from racing on the same
`data/` files / registry snapshots. Each subprocess mode
(game launcher, kill, force-user-game) is allowed to coexist with the
main GUI — they use a different mutex name suffix so the guard is
per-role, not strictly app-wide.
"""

import ctypes
import logging
from ctypes import wintypes
from typing import Optional

logger = logging.getLogger(__name__)

ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


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
