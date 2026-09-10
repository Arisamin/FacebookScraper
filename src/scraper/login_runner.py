"""Standalone interactive login runner: Opens visible browser and captures cookies."""

import os
import sys
import time
import json
import argparse
from playwright.sync_api import sync_playwright

def run_login(timeout_seconds: int = 120, storage_path: str = "session_storage.json") -> bool:
    print(f"[LoginRunner] Launching visible Chromium login window (timeout: {timeout_seconds}s)...")
    
    anti_detection_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-features=IsolateOrigins,site-per-process",
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=anti_detection_args,
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://www.facebook.com")
        
        start_time = time.time()
        logged_in = False
        
        while time.time() - start_time < timeout_seconds:
            try:
                cookies = context.cookies()
                cookie_names = [c["name"] for c in cookies]
                if "c_user" in cookie_names or "xs" in cookie_names:
                    print("[LoginRunner] Authentication cookies detected (c_user/xs). Finalizing session...")
                    time.sleep(2)  # Allow tokens to settle
                    state = context.storage_state()
                    with open(storage_path, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=2)
                    logged_in = True
                    break
            except Exception as e:
                print(f"[LoginRunner] Polling warning: {e}")
            
            time.sleep(1.5)
            
        browser.close()
        return logged_in


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook Interactive Login")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--output", type=str, default="session_storage.json", help="Path to save storage state")
    args = parser.parse_args()
    
    success = run_login(timeout_seconds=args.timeout, storage_path=args.output)
    sys.exit(0 if success else 1)
