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

    async def launch_interactive_login(self, timeout_seconds: int = 120) -> bool:
        """Launch a visible Chromium window to allow the user to log in and save session."""
        from playwright.async_api import async_playwright
        import asyncio

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=self.get_anti_detection_args(),
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            await page.goto("https://www.facebook.com")

            # Wait for user to log in by polling for common logged-in indicators
            # or until timeout
            start_time = asyncio.get_event_loop().time()
            logged_in = False
            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                cookies = await context.cookies()
                # Check for standard Facebook authentication cookies (c_user, xs)
                cookie_names = [c["name"] for c in cookies]
                if "c_user" in cookie_names or "xs" in cookie_names:
                    logged_in = True
                    break
                await asyncio.sleep(2)

            if logged_in:
                state = await context.storage_state()
                self.save_storage_state(state)

            await browser.close()
            return logged_in

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
