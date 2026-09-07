"""Data models for extracted posts and group audit records."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PostPayload(BaseModel):
    post_id: str
    group_name: Optional[str] = None
    author_name: Optional[str] = None
    author_profile_url: Optional[str] = None
    timestamp_str: Optional[str] = None
    published_iso: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_text: str = ""
    content_text: str = ""
    snippet: str = ""
    price: Optional[float] = None
    extracted_price: Optional[float] = None
    extracted_location: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    permalink: str = ""
    post_url: str = ""
    matched_filters: List[str] = Field(default_factory=list)
    match_score: float = 1.0
    requires_joining: bool = False

    def model_post_init(self, __context) -> None:
        if not self.content_text and self.raw_text:
            self.content_text = self.raw_text
        elif not self.raw_text and self.content_text:
            self.raw_text = self.content_text

        if self.price is not None and self.extracted_price is None:
            self.extracted_price = self.price
        elif self.extracted_price is not None and self.price is None:
            self.price = self.extracted_price

        if not self.post_url and self.permalink:
            self.post_url = self.permalink
        elif not self.permalink and self.post_url:
            self.permalink = self.post_url


class GroupRecord(BaseModel):
    group_name: str
    group_url: Optional[str] = None
    requires_joining: bool = False
    is_accessible: bool = True
    privacy_status: Optional[str] = "public"
    member_count_str: Optional[str] = None
    posts_scanned: int = 0
    matched_posts_count: int = 0

