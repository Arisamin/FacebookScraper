"""DOM Extractor: Parses accessibility trees, HTML nodes, and post elements from Facebook."""

import re
import uuid
from typing import Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.models.post import PostPayload


class DOMExtractor:
    """Extracts structured post metadata and text content from Facebook DOM nodes."""

    def extract_from_html(self, html_snippet: str, group_name: Optional[str] = None) -> PostPayload:
        soup = BeautifulSoup(html_snippet, "html.parser")

        # 1. Author extraction
        author = "Unknown Author"
        # Check standard headings and strong tags in post header
        h_tag = soup.find(["h2", "h3", "h4", "strong"])
        if h_tag and h_tag.get_text(strip=True):
            candidate = h_tag.get_text(strip=True)
            if len(candidate) < 60 and not candidate.startswith("http"):
                author = candidate

        if author == "Unknown Author":
            author_container = soup.find(class_=re.compile(r"author|user|actor", re.IGNORECASE))
            if author_container:
                author = author_container.get_text(strip=True)

        if author == "Unknown Author":
            # Fallback to profile link text
            prof_link = soup.find("a", href=re.compile(r"user/|profile\.php|/groups/[^/]+/user/"))
            if prof_link and prof_link.get_text(strip=True):
                author = prof_link.get_text(strip=True)

        if author == "Unknown Author":
            # Fallback to article aria-label
            article = soup.find(attrs={"role": "article"})
            if article and article.get("aria-label"):
                label = article["aria-label"]
                match = re.search(r"Post by ([\w\s]+)", label)
                if match:
                    author = match.group(1).strip()

        # 2. Text / Content extraction
        text_elements = soup.find_all(attrs={"dir": "auto"})
        if text_elements:
            content_text = " ".join(el.get_text(strip=True) for el in text_elements if el.get_text(strip=True))
        else:
            content_text = soup.get_text(separator=" ", strip=True)

        # 3. Post URL / Permalink extraction
        post_url = ""
        link_elem = soup.find("a", href=re.compile(r"posts/|permalink/|story_fbid="))
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            if href.startswith("/"):
                post_url = f"https://www.facebook.com{href}"
            else:
                post_url = href
        else:
            # Fallback: look for any permalink
            links = soup.find_all("a", href=True)
            for a in links:
                if "facebook.com" in a["href"]:
                    post_url = a["href"]
                    break

        # 4. Timestamp / Published date
        time_elem = soup.find(class_=re.compile(r"timestamp|time", re.IGNORECASE)) or soup.find("abbr")
        raw_time = time_elem.get("title") or time_elem.get_text(strip=True) if time_elem else "Just now"
        published_at = self.parse_relative_date(raw_time)

        # 5. Price extraction
        price = self.extract_price(content_text)

        # 6. Generate snippet
        snippet = self.generate_snippet(content_text, max_words=40)

        post_id = f"fb-{uuid.uuid4().hex[:10]}"

        return PostPayload(
            post_id=post_id,
            group_name=group_name,
            author_name=author,
            published_at=published_at,
            content_text=content_text,
            price=price,
            post_url=post_url or "https://facebook.com",
            snippet=snippet,
        )

    def generate_snippet(self, text: str, max_words: int = 40) -> str:
        """Truncate text to max_words and append ellipsis if truncated."""
        words = text.split()
        if len(words) <= max_words:
            return " ".join(words)
        return " ".join(words[:max_words]) + "..."

    def extract_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text."""
        if re.search(r"\bfree\b|חינם|למסירה", text, re.IGNORECASE):
            return 0.0

        match = re.search(r"(?:price:?|asking\s+for|budget\s+(?:up\s+to\s+)?|₪|\$|€|nis)\s*(\d+(?:,\d{3})*(?:\.\d+)?|\d+)", text, re.IGNORECASE)
        if match:
            raw_num = match.group(1).replace(",", "")
            return float(raw_num)

        match2 = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?|\d+)\s*(?:₪|nis|ils|\$|€|shekels?)", text, re.IGNORECASE)
        if match2:
            raw_num = match2.group(1).replace(",", "")
            return float(raw_num)

        return None

    def parse_relative_date(self, date_str: str) -> datetime:
        """Parse Facebook relative date strings in English and Hebrew (e.g. '2 hours ago', 'אתמול', 'לפני 3 שעות')."""
        now = datetime.now()
        clean = date_str.lower().strip()

        # English parsing
        if "min" in clean:
            match = re.search(r"(\d+)\s*m", clean)
            mins = int(match.group(1)) if match else 5
            return now - timedelta(minutes=mins)

        if "hour" in clean or "hr" in clean or "h" in clean:
            match = re.search(r"(\d+)\s*h", clean)
            hours = int(match.group(1)) if match else 1
            return now - timedelta(hours=hours)

        if "yesterday" in clean or "אתמול" in clean:
            return now - timedelta(days=1)

        if "שלשום" in clean or "לפני יומיים" in clean:
            return now - timedelta(days=2)

        if "day" in clean or "d" in clean or "ימים" in clean or "יום" in clean:
            match = re.search(r"(\d+)\s*(?:d|ימים|יום)", clean)
            days = int(match.group(1)) if match else 1
            return now - timedelta(days=days)

        if "week" in clean or "w" in clean or "שבועות" in clean or "שבוע" in clean:
            match = re.search(r"(\d+)\s*(?:w|שבועות|שבוע)", clean)
            weeks = int(match.group(1)) if match else 1
            return now - timedelta(weeks=weeks)

        if "שעתיים" in clean:
            return now - timedelta(hours=2)

        if "שעות" in clean or "שעה" in clean:
            match = re.search(r"(\d+)\s*(?:שעות|שעה)", clean)
            hours = int(match.group(1)) if match else 1
            return now - timedelta(hours=hours)

        if "דקות" in clean or "דקה" in clean:
            match = re.search(r"(\d+)\s*(?:דקות|דקה)", clean)
            mins = int(match.group(1)) if match else 5
            return now - timedelta(minutes=mins)

        return now
