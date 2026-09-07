"""Unit tests for Group Scanner & Privacy Gating detection."""

import pytest
from datetime import datetime, timedelta
from src.scraper.group_scanner import GroupScanner
from src.models.manifest import FilterCriteria, PrivacyHandling
from src.models.post import PostPayload, GroupRecord


class TestGroupScanner:
    """Test suite for detecting gated groups and filtering posts against criteria."""

    def test_detect_gated_private_group(self):
        scanner = GroupScanner()
        html_private = """
        <div>
            <h1>Furniture Lovers Israel</h1>
            <div role="button" aria-label="Join group">Join group</div>
            <div>This group is private. Join this group to view or participate in discussions.</div>
        </div>
        """
        is_gated = scanner.check_is_gated(html_private)
        assert is_gated is True

    def test_detect_public_open_group(self):
        scanner = GroupScanner()
        html_public = """
        <div>
            <h1>Open Second Hand Tel Aviv</h1>
            <div role="feed">
                <div role="article">Post content 1</div>
            </div>
        </div>
        """
        is_gated = scanner.check_is_gated(html_public)
        assert is_gated is False

    def test_create_gated_record(self):
        scanner = GroupScanner()
        record: GroupRecord = scanner.create_gated_record(
            group_name="Secret Furniture Deals",
            group_url="https://facebook.com/groups/secretfurniture",
        )
        assert record.group_name == "Secret Furniture Deals"
        assert record.requires_joining is True
        assert record.is_accessible is False

    def test_filter_post_matching_intent_and_timeframe(self):
        scanner = GroupScanner()
        criteria = FilterCriteria(
            include_keywords=["used furniture", "table"],
            exclude_keywords=["broken"],
            timeframe_days=30,
            price_max=1500.0,
            intent="buyer_request",
        )

        valid_post = PostPayload(
            post_id="p1",
            group_name="Furniture Israel",
            author_name="Sarah Levi",
            published_at=datetime.now() - timedelta(days=5),
            content_text="Looking to buy a used furniture set with a wooden table in good condition for 1000 NIS.",
            price=1000.0,
            post_url="https://facebook.com/p1",
        )

        assert scanner.matches_criteria(valid_post, criteria) is True

    def test_filter_post_excluding_negative_keywords(self):
        scanner = GroupScanner()
        criteria = FilterCriteria(
            include_keywords=["table"],
            exclude_keywords=["broken", "damaged"],
            timeframe_days=30,
        )

        post_with_bad_word = PostPayload(
            post_id="p2",
            group_name="Furniture Israel",
            author_name="Eli",
            published_at=datetime.now() - timedelta(days=2),
            content_text="Wooden table, but broken leg.",
            post_url="https://facebook.com/p2",
        )

        assert scanner.matches_criteria(post_with_bad_word, criteria) is False

    def test_filter_post_outdated_timeframe(self):
        scanner = GroupScanner()
        criteria = FilterCriteria(
            timeframe_days=14,
        )

        old_post = PostPayload(
            post_id="p3",
            group_name="Furniture Israel",
            author_name="David",
            published_at=datetime.now() - timedelta(days=45),
            content_text="Selling vintage closet.",
            post_url="https://facebook.com/p3",
        )

        assert scanner.matches_criteria(old_post, criteria) is False
