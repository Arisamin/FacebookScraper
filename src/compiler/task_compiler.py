"""Task Compiler: Parses natural language scraping requests into structured TaskManifests."""

import os
import re
import json
import uuid
from typing import Optional, Callable, Dict, Any, List

from src.models.manifest import (
    TaskManifest,
    TargetConfig,
    TargetType,
    FilterCriteria,
    OutputConfig,
    OutputFormat,
    ActionConfig,
    ActionType,
    PrivacyHandling,
)
from src.compiler.prompt_templates import SYSTEM_COMPILER_PROMPT


class TaskCompiler:
    """Compiles human-readable natural language prompts into executable TaskManifest objects."""

    def __init__(self, llm_client: Optional[Callable[[str], Dict[str, Any]]] = None):
        """
        Initialize the compiler.
        :param llm_client: Optional custom callable taking a prompt and returning a dict.
        """
        self.llm_client = llm_client

    def compile(self, prompt: str) -> TaskManifest:
        """
        Compile a human-readable prompt into a TaskManifest.
        Raises ValueError if the prompt is empty or invalid.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or whitespace.")

        clean_prompt = prompt.strip()

        # 1. If custom LLM client is provided, use it
        if self.llm_client:
            raw_data = self.llm_client(clean_prompt)
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            return TaskManifest.model_validate(raw_data)

        # 2. If OpenAI API key is present in environment, call LLM
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            try:
                return self._call_openai(clean_prompt, openai_key)
            except Exception:
                # Fallback to heuristic parser on API error/timeout
                pass

        # 3. Deterministic heuristic compiler (offline / test mode)
        return self._heuristic_compile(clean_prompt)

    def _call_openai(self, prompt: str, api_key: str) -> TaskManifest:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=os.getenv("COMPILER_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_COMPILER_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return TaskManifest.model_validate(data)

    def _heuristic_compile(self, prompt: str) -> TaskManifest:
        """Deterministic heuristic rule-based parser for offline execution and testing."""
        prompt_lower = prompt.lower()
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # Target Detection
        target_type = TargetType.GROUP_SEARCH
        url_or_query = ""
        location = None
        max_posts = 50

        # Scan limits
        posts_limit_match = re.search(r"(?:extract|find|get|scrape|latest|top)\s+(\d+)\s+posts?", prompt_lower)
        if posts_limit_match:
            max_posts = int(posts_limit_match.group(1))

        if "marketplace" in prompt_lower:
            target_type = TargetType.MARKETPLACE
            # extract query after 'for' or 'search marketplace for'
            match = re.search(r"marketplace\s+(?:for\s+)?([^,]+?)(?:\s+under|\s+in|\s+with|\s+export|$)", prompt, re.IGNORECASE)
            url_or_query = match.group(1).strip() if match else "marketplace items"
        elif "facebook.com/groups/" in prompt_lower:
            target_type = TargetType.GROUP
            match = re.search(r"https?://(?:www\.)?facebook\.com/groups/[a-zA-Z0-9._-]+", prompt)
            url_or_query = match.group(0) if match else "https://facebook.com/groups/"
        elif "facebook.com/" in prompt_lower and not "groups" in prompt_lower:
            target_type = TargetType.PAGE
            match = re.search(r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+", prompt)
            url_or_query = match.group(0) if match else "https://facebook.com/"
        elif "group" in prompt_lower:
            target_type = TargetType.GROUP_SEARCH
            match = re.search(r"including the word ['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            if match:
                url_or_query = match.group(1).strip()
            else:
                match_named = re.search(r"(?:from|in|about)\s+(?:the\s+)?(['\"]?)([A-Za-z0-9\s._-]+?)\1\s+(?:group|page)", prompt, re.IGNORECASE)
                if match_named:
                    url_or_query = match_named.group(2).strip()
                else:
                    match2 = re.search(r"search in all groups (?:about|for|named|with)?\s*([^,\.]+)", prompt, re.IGNORECASE)
                    url_or_query = match2.group(1).strip() if match2 else "facebook groups"

        # Location detection (ignoring formatting words like Markdown, CSV, JSON, Table)
        format_words = {"markdown", "table", "csv", "json", "mermaid", "diagram", "summary", "which", "all", "the", "a"}
        loc_match = re.search(r"\bin\s+([A-Z][a-zA-Z\s]+?)(?:,|\s+in\s+which|\s+under|\s+export|\s+output|$)", prompt)
        if loc_match:
            loc_candidate = loc_match.group(1).strip()
            if loc_candidate.lower() not in format_words:
                location = loc_candidate
        elif "israel" in prompt_lower:
            location = "Israel"
        elif "tel aviv" in prompt_lower:
            location = "Tel Aviv"
        elif "jerusalem" in prompt_lower:
            location = "Jerusalem"

        # Criteria & Timeframe
        timeframe_days = 30
        if "month" in prompt_lower:
            timeframe_days = 30
        elif "week" in prompt_lower:
            timeframe_days = 7
        elif "year" in prompt_lower:
            timeframe_days = 365
        match_days = re.search(r"last\s+(\d+)\s+days?", prompt_lower)
        if match_days:
            timeframe_days = int(match_days.group(1))

        # Intent
        intent = None
        if any(w in prompt_lower for w in ["asking to buy", "looking to buy", "want to buy", "seeking used", "buying"]):
            intent = "buyer_request"
        elif any(w in prompt_lower for w in ["selling", "for sale", "offering"]):
            intent = "seller_offering"

        # Price extraction
        price_max = None
        price_match = re.search(r"under\s+(\d+(?:\.\d+)?)\s*(?:nis|ils|\$|€|shekels?)?", prompt_lower)
        if price_match:
            price_max = float(price_match.group(1))

        # Keyword inclusion / exclusion
        exclude_keywords: List[str] = []
        exclude_match = re.search(r"(?:ignore|exclude|without)\s+([^,\.]+)", prompt_lower)
        if exclude_match:
            exclude_raw = exclude_match.group(1)
            parts = re.split(r"\s+and\s+|\s*,\s*", exclude_raw)
            exclude_keywords = [p.strip() for p in parts if p.strip()]

        include_keywords: List[str] = []
        if "used furniture" in prompt_lower:
            include_keywords.append("used furniture")
        if "2-3 room" in prompt_lower:
            include_keywords.append("2-3 room")

        # Output Config & Custom Columns
        out_format = OutputFormat.CSV
        if "markdown table" in prompt_lower or "markdown" in prompt_lower or "table" in prompt_lower:
            out_format = OutputFormat.MARKDOWN_TABLE
        elif "json" in prompt_lower:
            out_format = OutputFormat.JSON
        elif "diagram" in prompt_lower or "mermaid" in prompt_lower:
            out_format = OutputFormat.DIAGRAM_MERMAID
        elif "summary" in prompt_lower:
            out_format = OutputFormat.EXECUTIVE_SUMMARY

        columns: Optional[List[str]] = None
        if "|" in prompt:
            col_match = re.search(r"columns:\s*([^,\.\n]+(?:\|[^,\.\n]+)+)", prompt, re.IGNORECASE)
            if col_match:
                raw_cols = col_match.group(1)
                columns = [c.strip() for c in raw_cols.split("|") if c.strip()]

        snippet_words = 40
        snippet_match = re.search(r"snippet\s*\((?:up to\s*)?(\d+)\s*words\)", prompt_lower)
        if snippet_match:
            snippet_words = int(snippet_match.group(1))

        # Privacy handling (gated groups)
        record_gated = False
        if any(w in prompt_lower for w in ["requires joining", "without first joining", "not allow seeing the posts", "join"]):
            record_gated = True

        # Actions (Telegram / Webhook)
        actions: List[ActionConfig] = []
        tg_match = re.search(r"telegram\s+(?:alert\s+to\s+|to\s+channel\s+|to\s+)(\d+)", prompt_lower)
        if tg_match:
            actions.append(
                ActionConfig(
                    type=ActionType.TELEGRAM,
                    target_config={"channel_id": tg_match.group(1).strip()},
                )
            )

        return TaskManifest(
            task_id=task_id,
            description=prompt[:120],
            target=TargetConfig(
                type=target_type,
                url_or_query=url_or_query or "facebook search",
                location=location,
                max_posts_to_scan=max_posts,
                max_scrolls=10,
            ),
            criteria=FilterCriteria(
                include_keywords=include_keywords,
                exclude_keywords=exclude_keywords,
                timeframe_days=timeframe_days,
                price_max=price_max,
                intent=intent,
            ),
            output_config=OutputConfig(
                format=out_format,
                columns=columns,
                snippet_max_words=snippet_words,
            ),
            privacy_handling=PrivacyHandling(
                record_gated_groups=record_gated,
                auto_request_join=False,
            ),
            actions=actions,
        )
