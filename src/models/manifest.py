"""Data models and schemas for Task Manifests and Extracted Post Payloads."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TargetType(str, Enum):
    GROUP = "group"
    GROUP_SEARCH = "group_search"
    SEARCH = "search"
    PAGE = "page"
    MARKETPLACE = "marketplace"


class OutputFormat(str, Enum):
    MARKDOWN_TABLE = "markdown_table"
    HTML_TABLE = "html_table"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    LATEX = "latex"
    EXECUTIVE_SUMMARY = "executive_summary"
    MERMAID_DIAGRAM = "mermaid_diagram"
    CUSTOM = "custom"


class ActionType(str, Enum):
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SAVE_FILE = "save_file"
    EMAIL = "email"


class ActionConfig(BaseModel):
    type: ActionType
    target_config: Dict[str, Any] = Field(default_factory=dict)


class TargetConfig(BaseModel):
    type: TargetType
    url_or_query: str
    location: Optional[str] = None
    max_posts_to_scan: int = 30
    max_scrolls: int = 10


class FilterCriteria(BaseModel):
    include_keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    intent: Optional[str] = None  # e.g. "buyer_request", "seller_offer", "general"
    timeframe_days: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    location_filter: Optional[str] = None
    semantic_condition: Optional[str] = None


class OutputConfig(BaseModel):
    format: str = "markdown_table"
    custom_instructions: Optional[str] = None
    columns: Optional[List[str]] = None
    snippet_max_words: Optional[int] = 40
    destination_path: Optional[str] = None


class PrivacyHandling(BaseModel):
    record_gated_groups: bool = True


class TaskManifest(BaseModel):
    task_id: str
    description: str
    target: TargetConfig
    criteria: FilterCriteria = Field(default_factory=FilterCriteria)
    output_config: OutputConfig = Field(default_factory=OutputConfig)
    privacy_handling: PrivacyHandling = Field(default_factory=PrivacyHandling)
    actions: List[ActionConfig] = Field(default_factory=list)
