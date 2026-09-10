"""Session Manager: Handles cookies, storage states, anti-detection browser profile configurations."""

import os
import sys
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = logging.getLogger("SessionManager")


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

    async def check_live_session(self) -> bool:
        """
        Actively probe Facebook to verify if the session cookies are still accepted
        or if Facebook has expired them with a password prompt / login wall.
        """
        if not self.has_valid_session():
            return False

        def _run_check() -> bool:
            import subprocess
            cmd = [sys.executable, "-m", "src.scraper.session_checker", "--storage", self.storage_state_path]
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=25)
                return res.returncode == 0
            except Exception as e:
                logger.warning(f"Session check subprocess error: {e}")
                return False

        return await asyncio.to_thread(_run_check)

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

    async def launch_interactive_login(self, timeout_seconds: int = 120) -> bool:
        """Launch a visible Chromium window in an isolated process to allow user login."""
        def _run_login() -> bool:
            import subprocess
            cmd = [
                sys.executable,
                "-m",
                "src.scraper.login_runner",
                "--timeout",
                str(timeout_seconds),
                "--output",
                self.storage_state_path,
            ]
            try:
                logger.info(f"Launching visible login window via login_runner (timeout: {timeout_seconds}s)...")
                res = subprocess.run(cmd, timeout=timeout_seconds + 10)
                return res.returncode == 0
            except Exception as e:
                logger.error(f"Error executing login runner: {e}")
                return False

        return await asyncio.to_thread(_run_login)

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
