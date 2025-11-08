import threading
from typing import Any, Optional


class StatusBroadcaster:
    def __init__(self) -> None:
        self._status: Any = None
        self._status_changed = threading.Event()
        self._lock = threading.Lock()

    def set_status(self, new_status: Any) -> None:
        with self._lock:
            if self._status != new_status:
                self._status = new_status
                self._status_changed.set()

    def get_status(self) -> Any:
        with self._lock:
            return self._status

    def wait_for_status_change(self, timeout: Optional[float] = None) -> Any:
        """Wait for status to change and return the new status"""
        if self._status_changed.wait(timeout):
            self._status_changed.clear()
            return self.get_status()
        return None
