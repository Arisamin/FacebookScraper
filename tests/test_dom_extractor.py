"""Unit tests for DOM Extractor & Text Parsing from Facebook HTML / accessibility structures."""

import pytest
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.scraper.dom_extractor import DOMExtractor
from src.models.post import PostPayload


class TestDOMExtractor:
    """Test suite for extracting structured post payloads from Facebook DOM elements."""

    def test_parse_post_with_standard_layout(self):
        html = """
        <div role="article" aria-label="Post by Dan Cohen">
            <div class="author-container"><a href="/dan.cohen">Dan Cohen</a></div>
            <div class="timestamp-container"><span title="Yesterday at 14:30">Yesterday at 14:30</span></div>
            <div dir="auto" class="post-text">
                Looking to buy a used dining table with 4 chairs in Tel Aviv. Budget up to 1200 NIS.
            </div>
            <a href="https://facebook.com/groups/123/posts/99999">Permalink</a>
        </div>
        """
        extractor = DOMExtractor()
        post: PostPayload = extractor.extract_from_html(html, group_name="Tel Aviv Buy/Sell")

        assert post is not None
        assert post.author_name == "Dan Cohen"
        assert "dining table" in post.content_text
        assert post.group_name == "Tel Aviv Buy/Sell"
        assert post.post_url == "https://facebook.com/groups/123/posts/99999"

    def test_extract_snippet_with_word_limit(self):
        extractor = DOMExtractor()
        long_text = "Word " * 100
        snippet = extractor.generate_snippet(long_text, max_words=40)
        words = snippet.split()
        assert len(words) <= 41  # 40 words + possible ellipsis
        assert snippet.endswith("...")

    def test_clean_price_extraction(self):
        extractor = DOMExtractor()
        assert extractor.extract_price("Price: 500 NIS") == 500.0
        assert extractor.extract_price("Asking for 2,400 ₪ only") == 2400.0
        assert extractor.extract_price("Free giveaway") == 0.0
        assert extractor.extract_price("No price mentioned here") is None

    def test_parse_fuzzy_dates(self):
        extractor = DOMExtractor()
        now = datetime.now()

        d_hours = extractor.parse_relative_date("2 hours ago")
        assert (now - d_hours).total_seconds() < 7500

        d_days = extractor.parse_relative_date("3 days ago")
        assert (now - d_days).days in [2, 3]

        d_yesterday = extractor.parse_relative_date("Yesterday at 10:00")
        assert 80000 <= (now - d_yesterday).total_seconds() <= 90000
