import threading

class StatusBroadcaster:
    def __init__(self):
        self._status = None
        self._status_changed = threading.Event()
        self._lock = threading.Lock()
        
    def set_status(self, new_status):
        with self._lock:
            if self._status != new_status:
                self._status = new_status
                self._status_changed.set()
    
    def get_status(self):
        with self._lock:
            return self._status
    
    def wait_for_status_change(self, timeout=None):
        """Wait for status to change and return the new status"""
        if self._status_changed.wait(timeout):
            self._status_changed.clear()
            return self.get_status()
        return None