"""Session Manager: Handles cookies, storage states, anti-detection browser profile configurations."""

import os
import json
from typing import Optional, Dict, Any, List


class SessionManager:
    """Manages persistent browser storage states and cookies for authenticated sessions."""

    def __init__(self, storage_state_path: Optional[str] = None):
        self.storage_state_path = storage_state_path or os.getenv(
            "FB_STORAGE_STATE_PATH", "session_storage.json"
        )

    def has_valid_session(self) -> bool:
        """Check if storage state file exists and has non-empty cookies."""
        if not os.path.exists(self.storage_state_path):
            return False
        try:
            with open(self.storage_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookies = data.get("cookies", [])
                return len(cookies) > 0
        except Exception:
            return False

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        """Load storage state dictionary if file exists."""
        if self.has_valid_session():
            with open(self.storage_state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_storage_state(self, state: Dict[str, Any]) -> None:
        """Save storage state dictionary to disk."""
        with open(self.storage_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def get_anti_detection_args(self) -> List[str]:
        """Browser launch flags to minimize bot detection."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--hide-scrollbars",
            "--mute-audio",
        ]
