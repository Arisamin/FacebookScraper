"""Group Scanner: Manages group discovery, privacy detection, and criteria matching."""

import re
from typing import Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from src.models.manifest import FilterCriteria
from src.models.post import PostPayload, GroupRecord


class GroupScanner:
    """Detects group privacy status and filters posts against structured criteria."""

    def check_is_gated(self, html_snippet: str) -> bool:
        """
        Check if a group requires joining to view posts.
        Returns True if the group is private or gated.
        """
        soup = BeautifulSoup(html_snippet, "html.parser")
        text = soup.get_text(separator=" ", strip=True).lower()

        gated_indicators = [
            "join this group to view",
            "this group is private",
            "group is private",
            "join group to see posts",
            "only members can see who's in the group",
            "קבוצה פרטית",
            "הצטרף לקבוצה כדי",
        ]

        for indicator in gated_indicators:
            if indicator in text:
                return True

        # Check for Join button presence without feed
        join_btn = soup.find(attrs={"aria-label": re.compile(r"join group|הצטרף", re.IGNORECASE)})
        feed = soup.find(attrs={"role": "feed"})
        articles = soup.find_all(attrs={"role": "article"})

        if join_btn and not feed and len(articles) == 0:
            return True

        return False

    def create_gated_record(self, group_name: str, group_url: str = "") -> GroupRecord:
        """Create a structured GroupRecord for a locked/private group."""
        return GroupRecord(
            group_name=group_name,
            group_url=group_url,
            requires_joining=True,
            is_accessible=False,
            privacy_status="private",
        )

    def matches_criteria(self, post: PostPayload, criteria: FilterCriteria) -> bool:
        """Check if a post fulfills all filter criteria."""
        content_lower = post.content_text.lower()

        # 1. Exclude keywords
        for exc in criteria.exclude_keywords:
            if exc.lower() in content_lower:
                return False

        # 2. Include keywords (if any specified, at least one or all must match)
        if criteria.include_keywords:
            matched = any(inc.lower() in content_lower for inc in criteria.include_keywords)
            if not matched:
                return False

        # 3. Timeframe check
        if criteria.timeframe_days and post.published_at:
            cutoff = datetime.now() - timedelta(days=criteria.timeframe_days)
            if post.published_at < cutoff:
                return False

        # 4. Price ceiling check
        if criteria.price_max is not None and post.price is not None:
            if post.price > criteria.price_max:
                return False

        # 5. Price floor check
        if criteria.price_min is not None and post.price is not None:
            if post.price < criteria.price_min:
                return False

        # 6. Intent check
        if criteria.intent:
            if criteria.intent == "buyer_request":
                buyer_indicators = ["looking to buy", "asking to buy", "want to buy", "מחפש לקנות", "מעוניין לקנות", "seeking", "budget"]
                if not any(ind in content_lower for ind in buyer_indicators):
                    return False
            elif criteria.intent == "seller_offering":
                seller_indicators = ["for sale", "selling", "למכירה", "למסירה", "offering"]
                if not any(ind in content_lower for ind in seller_indicators):
                    return False

        return True
