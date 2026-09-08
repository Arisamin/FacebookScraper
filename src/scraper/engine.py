"""Scraper Engine: Main browser orchestrator combining DOM extraction, gating checks, and AI vision recovery."""

import asyncio
import logging
from typing import List, Tuple, Optional, Callable
from playwright.async_api import async_playwright, Page, BrowserContext

from src.models.manifest import TaskManifest, TargetType
from src.models.post import PostPayload, GroupRecord
from src.scraper.session_manager import SessionManager
from src.scraper.dom_extractor import DOMExtractor
from src.scraper.group_scanner import GroupScanner
from src.scraper.vision_fallback import VisionFallbackHandler

logger = logging.getLogger(__name__)


class ScraperEngine:
    """Orchestrates Facebook scraping execution based on a compiled TaskManifest."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        dom_extractor: Optional[DOMExtractor] = None,
        group_scanner: Optional[GroupScanner] = None,
        vision_handler: Optional[VisionFallbackHandler] = None,
    ):
        self.session_manager = session_manager or SessionManager()
        self.dom_extractor = dom_extractor or DOMExtractor()
        self.group_scanner = group_scanner or GroupScanner()
        self.vision_handler = vision_handler or VisionFallbackHandler()

    async def execute_task(
        self,
        manifest: TaskManifest,
        headless: bool = True,
        page_override: Optional[Page] = None,
    ) -> Tuple[List[PostPayload], List[GroupRecord]]:
        """
        Executes real scraping against Facebook for the given TaskManifest.
        Returns a tuple of (matched_posts, group_records).
        """
        posts: List[PostPayload] = []
        group_records: List[GroupRecord] = []

        if page_override:
            # Used in unit/integration tests with mocked or injected page
            return await self._scrape_page(page_override, manifest)

        async with async_playwright() as p:
            launch_args = self.session_manager.get_anti_detection_args()
            browser = await p.chromium.launch(headless=headless, args=launch_args)

            storage_state = self.session_manager.load_storage_state()
            context: BrowserContext = await browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            page: Page = await context.new_page()
            try:
                posts, group_records = await self._scrape_page(page, manifest)
            finally:
                await context.close()
                await browser.close()

        return posts, group_records

    async def _scrape_page(
        self, page: Page, manifest: TaskManifest
    ) -> Tuple[List[PostPayload], List[GroupRecord]]:
        posts: List[PostPayload] = []
        group_records: List[GroupRecord] = []

        target = manifest.target

        # 1. Navigation
        if target.type == TargetType.GROUP or target.type == TargetType.PAGE:
            url = target.url_or_query
            await page.goto(url, wait_until="domcontentloaded")
            content = await page.content()

            # Check if gated
            if self.group_scanner.check_is_gated(content):
                if manifest.privacy_handling.record_gated_groups:
                    group_records.append(
                        self.group_scanner.create_gated_record(
                            group_name=target.url_or_query,
                            group_url=target.url_or_query,
                        )
                    )
                return posts, group_records

            extracted_posts = await self._extract_posts_from_feed(page, manifest)
            posts.extend(extracted_posts)

        elif target.type == TargetType.GROUP_SEARCH:
            # 1. Search for groups
            import urllib.parse
            encoded_q = urllib.parse.quote_plus(target.url_or_query)
            search_url = f"https://www.facebook.com/search/groups/?q={encoded_q}"
            await page.goto(search_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # 2. Extract group links from search results
            group_links = []
            anchor_elements = await page.query_selector_all('a[href*="/groups/"]')
            for a in anchor_elements:
                href = await a.get_attribute("href")
                if href and "/groups/" in href and not "/search/" in href:
                    # Clean URL to standard group base URL
                    clean_url = href.split("?")[0]
                    if clean_url not in group_links:
                        group_links.append(clean_url)
                if len(group_links) >= 3:
                    break

            if not group_links:
                # If no direct group search cards found, record search record
                group_records.append(
                    GroupRecord(
                        group_name=f"Search: {target.url_or_query}",
                        group_url=search_url,
                        requires_joining=False,
                        is_accessible=True,
                    )
                )

            # 3. Visit discovered group(s) and extract posts
            for g_url in group_links:
                try:
                    await page.goto(g_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2500)
                    content = await page.content()

                    if self.group_scanner.check_is_gated(content):
                        if manifest.privacy_handling.record_gated_groups:
                            group_records.append(
                                self.group_scanner.create_gated_record(
                                    group_name=g_url.split("/groups/")[-1].strip("/"),
                                    group_url=g_url,
                                )
                            )
                        continue

                    # Extract posts from this group
                    grp_title = await page.title()
                    clean_grp_name = grp_title.replace("| Facebook", "").replace("- Facebook", "").strip() or g_url.split("/groups/")[-1].strip("/")
                    g_posts = await self._extract_posts_from_feed(page, manifest, group_name=clean_grp_name)
                    posts.extend(g_posts)
                    group_records.append(
                        GroupRecord(
                            group_name=clean_grp_name,
                            group_url=g_url,
                            requires_joining=False,
                            is_accessible=True,
                            posts_scanned=len(g_posts),
                            matched_posts_count=len(g_posts),
                        )
                    )
                    if len(posts) >= manifest.target.max_posts_to_scan:
                        break
                except Exception as e:
                    logger.warning(f"Error scanning group {g_url}: {e}")

        return posts, group_records

    async def _extract_posts_from_feed(
        self, page: Page, manifest: TaskManifest, group_name: Optional[str] = None
    ) -> List[PostPayload]:
        matched_posts: List[PostPayload] = []
        max_scrolls = min(manifest.target.max_scrolls or 5, 5)

        for scroll_idx in range(max_scrolls):
            articles = await page.query_selector_all('div[role="article"], div[data-pagelet*="FeedUnit"]')

            for article in articles:
                try:
                    html = await article.inner_html()
                    post = self.dom_extractor.extract_from_html(html, group_name=group_name)

                    # Check criteria & duplicate prevention
                    if post.content_text and not any(p.content_text == post.content_text for p in matched_posts):
                        if self.group_scanner.matches_criteria(post, manifest.criteria):
                            if manifest.output_config.snippet_max_words:
                                post.snippet = self.dom_extractor.generate_snippet(
                                    post.content_text, manifest.output_config.snippet_max_words
                                )
                            matched_posts.append(post)

                    if len(matched_posts) >= manifest.target.max_posts_to_scan:
                        return matched_posts
                except Exception:
                    continue

            # Scroll down to trigger infinite feed loading
            await page.evaluate("window.scrollBy(0, 1200)")
            await page.wait_for_timeout(1500)

        return matched_posts
