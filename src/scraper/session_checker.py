"""Standalone live session checker: Probes Facebook for login wall without event-loop conflicts."""

import os
import sys
import json
import argparse
from playwright.sync_api import sync_playwright

def check_live(storage_path: str = "session_storage.json") -> bool:
    if not os.path.exists(storage_path):
        return False
        
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cookies = data.get("cookies", [])
            if not cookies:
                return False
    except Exception:
        return False

    anti_detection_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-features=IsolateOrigins,site-per-process",
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=anti_detection_args,
            )
            context = browser.new_context(
                storage_state=storage_path,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            try:
                page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(2500)
                body_text = page.inner_text("body")
                is_login_wall = (
                    "התחברות" in body_text or
                    "log in" in body_text.lower() or
                    "המשך" in body_text or
                    "continue as" in body_text.lower() or
                    "סיסמה" in body_text or
                    "password" in body_text.lower() or
                    "login" in page.url or
                    "checkpoint" in page.url
                )
                return not is_login_wall
            finally:
                context.close()
                browser.close()
    except Exception:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook Live Session Checker")
    parser.add_argument("--storage", type=str, default="session_storage.json", help="Path to storage state")
    args = parser.parse_args()
    
    is_valid = check_live(storage_path=args.storage)
    sys.exit(0 if is_valid else 1)
