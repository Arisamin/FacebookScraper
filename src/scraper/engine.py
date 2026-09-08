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
        is_direct_url = target.url_or_query.startswith("http://") or target.url_or_query.startswith("https://")

        # 1. Navigation for Direct URL
        if is_direct_url:
            url = target.url_or_query
            logger.info(f"Navigating directly to target URL: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            content = await page.content()

            # Check if gated
            if self.group_scanner.check_is_gated(content):
                logger.info(f"Target URL is gated/private: {url}")
                if manifest.privacy_handling.record_gated_groups:
                    group_records.append(
                        self.group_scanner.create_gated_record(
                            group_name=target.url_or_query.split("/groups/")[-1].strip("/"),
                            group_url=url,
                        )
                    )
                return posts, group_records

            grp_title = await page.title()
            clean_grp_name = grp_title.replace("| Facebook", "").replace("- Facebook", "").strip() or url.split("/groups/")[-1].strip("/")
            extracted_posts = await self._extract_posts_from_feed(page, manifest, group_name=clean_grp_name)
            logger.info(f"Extracted {len(extracted_posts)} posts directly from URL: {url}")
            posts.extend(extracted_posts)
            group_records.append(
                GroupRecord(
                    group_name=clean_grp_name,
                    group_url=url,
                    requires_joining=False,
                    is_accessible=True,
                    posts_scanned=len(extracted_posts),
                    matched_posts_count=len(extracted_posts),
                )
            )

        else:
            # Query-based search for groups
            import urllib.parse
            encoded_q = urllib.parse.quote_plus(target.url_or_query)
            search_url = f"https://www.facebook.com/search/groups/?q={encoded_q}"
            logger.info(f"Navigating to group search URL: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3500)

            # 2. Extract group links from search results
            group_links = []
            anchor_elements = await page.query_selector_all('a[href*="/groups/"]')
            for a in anchor_elements:
                href = await a.get_attribute("href")
                if not href:
                    continue
                # Normalize relative URLs
                if href.startswith("/"):
                    href = f"https://www.facebook.com{href}"
                elif not href.startswith("http"):
                    href = f"https://www.facebook.com/{href.lstrip('/')}"

                # Clean URL of query parameters
                clean_url = href.split("?")[0].rstrip("/")

                # Filter out generic Facebook navigation URLs
                parts = clean_url.split("/groups/")
                if len(parts) < 2:
                    continue
                group_id_slug = parts[1].split("/")[0].strip()
                if not group_id_slug or group_id_slug.lower() in ("feed", "discover", "joins", "create", "notifications", "search"):
                    continue

                canonical_group_url = f"https://www.facebook.com/groups/{group_id_slug}"
                if canonical_group_url not in group_links:
                    logger.info(f"Discovered group from search: {canonical_group_url}")
                    group_links.append(canonical_group_url)

                if len(group_links) >= 3:
                    break

            if not group_links:
                logger.warning(f"No direct group links found in search for query '{target.url_or_query}'")
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
                    logger.info(f"Visiting discovered group: {g_url}")
                    await page.goto(g_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                    content = await page.content()

                    if self.group_scanner.check_is_gated(content):
                        logger.info(f"Group is private/gated: {g_url}")
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
                    logger.info(f"Extracted {len(g_posts)} matched posts from group '{clean_grp_name}' ({g_url})")
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
            logger.info(f"Feed scroll {scroll_idx + 1}/{max_scrolls}: detected {len(articles)} article DOM nodes.")

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
            await page.wait_for_timeout(1800)

        return matched_posts
