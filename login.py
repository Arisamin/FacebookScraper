"""Interactive Facebook Login Helper: Captures and saves session_storage.json."""

import asyncio
from playwright.async_api import async_playwright
from src.scraper.session_manager import SessionManager


async def capture_session():
    session_manager = SessionManager()
    print("\n=======================================================")
    print("      Facebook Interactive Session Authenticator")
    print("=======================================================")
    print("1. A Chromium browser window will open.")
    print("2. Log into your Facebook account (and complete 2FA if needed).")
    print("3. Once logged in, return to this terminal and press Enter.")
    print("=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=session_manager.get_anti_detection_args(),
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await page.goto("https://www.facebook.com")

        print("Waiting for login... Press Enter in this terminal after you are logged in.")
        input("\n>>> Press ENTER here when you are logged into Facebook in the browser window <<<")

        state = await context.storage_state()
        session_manager.save_storage_state(state)
        print(f"\n✅ Session successfully captured and saved to: {session_manager.storage_state_path}")
        print("You can now transfer this file to your Hetzner server or run headless scrapes locally!\n")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture_session())
