# risk_plugins/message_throttling.py

from .base import RiskPlugin
import threading
import time
import logging

class MessageThrottlingCheck(RiskPlugin):
    def __init__(self, database):
        super().__init__(database)
        self.message_counts = {}
        self.lock = threading.Lock()
        self.reset_interval = 1  # Reset counts every second
        threading.Thread(target=self.reset_counts, daemon=True).start()

    def reset_counts(self):
        while True:
            time.sleep(self.reset_interval)
            with self.lock:
                self.message_counts.clear()

    def check(self, order, account, session_id, risk_settings):
        try:
            max_messages = risk_settings.get('max_messages_per_second', 100)
            with self.lock:
                count = self.message_counts.get(session_id, 0)
                if count >= max_messages:
                    return False, f"Message rate limit exceeded: {max_messages} messages per second."
                self.message_counts[session_id] = count + 1
            return True, ""
        except Exception as e:
            logging.error(f"MessageThrottlingCheck error: {e}")
            return False, "Error in message throttling check"

