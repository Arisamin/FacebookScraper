"""Output Synthesizer: Formats scraped posts and gated group records into arbitrary formats using AI or deterministic rules."""

import os
import io
import csv
import json
import logging
from typing import List, Optional, Dict, Any
from src.models.post import PostPayload, GroupRecord

logger = logging.getLogger("OutputSynthesizer")


class OutputSynthesizer:
    """Transforms scraped data structures into various user-requested formats using AI or deterministic formatters."""

    DEFAULT_COLUMNS = [
        "GroupName",
        "Requires joining (true/false)",
        "post link",
        "date of publish",
        "description snippet (up to 40 words)",
    ]

    def synthesize(
        self,
        posts: List[PostPayload],
        group_records: List[GroupRecord],
        format: str = "markdown_table",
        columns: Optional[List[str]] = None,
        custom_instructions: Optional[str] = None,
        original_prompt: Optional[str] = None,
    ) -> str:
        """
        Universal synthesis router.
        If standard format and no special AI instructions: use high-speed deterministic rules.
        If custom format (XML, YAML, LaTeX, HTML/CSS, custom schema) or AI instructions: invoke Google Gemini.
        """
        fmt_low = (format or "markdown_table").lower().strip()

        # If standard format and no custom instructions/prompt, use fast deterministic formatters
        if not custom_instructions:
            if fmt_low in ("csv",):
                return self.format_csv(posts, group_records, columns)
            elif fmt_low in ("markdown_table", "markdown", "md"):
                return self.format_markdown_table(posts, group_records, columns)
            elif fmt_low in ("html_table", "html"):
                return self.format_html_table(posts, group_records, columns)
            elif fmt_low in ("diagram_mermaid", "mermaid_diagram", "mermaid"):
                return self.format_mermaid_diagram(posts, group_records)
            elif fmt_low in ("json",):
                return self.format_json(posts, group_records)

        # For any custom or LLM-instructed format (XML, YAML, custom HTML, LaTeX, executive summary, etc.),
        # invoke Google Gemini AI Synthesizer
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                return self.ai_synthesize(
                    posts=posts,
                    group_records=group_records,
                    target_format=format,
                    custom_instructions=custom_instructions,
                    original_prompt=original_prompt,
                )
            except Exception as e:
                logger.warning(f"AI synthesizer call failed: {e}. Falling back to deterministic formatter.")

        # Fallback to standard deterministic formatters if AI is offline
        if "html" in fmt_low:
            return self.format_html_table(posts, group_records, columns)
        elif "csv" in fmt_low:
            return self.format_csv(posts, group_records, columns)
        elif "json" in fmt_low:
            return self.format_json(posts, group_records)
        else:
            return self.format_markdown_table(posts, group_records, columns)

    def ai_synthesize(
        self,
        posts: List[PostPayload],
        group_records: List[GroupRecord],
        target_format: str = "markdown_table",
        custom_instructions: Optional[str] = None,
        original_prompt: Optional[str] = None,
    ) -> str:
        """
        Use Google Gemini to format structured post payloads into any user-requested format
        (e.g., XML, YAML, LaTeX, HTML, custom markdown, executive summary, etc.).
        """
        import urllib.request
        import urllib.error

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY is not set.")

        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        posts_data = [
            {
                "group_name": p.group_name or "N/A",
                "author": p.author_name or "Unknown",
                "published_at": p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else (p.timestamp_str or "Recent"),
                "price": f"{p.price} NIS" if p.price is not None else None,
                "url": p.post_url or p.permalink or "N/A",
                "snippet": p.snippet or p.content_text,
            }
            for p in posts
        ]
        groups_data = [
            {
                "group_name": g.group_name,
                "url": g.group_url,
                "requires_joining": g.requires_joining,
            }
            for g in group_records
        ]

        system_instruction = (
            "You are an expert Data Synthesizer AI agent in an intelligent web scraping automation pipeline.\n"
            "Your task is to transform the provided structured Facebook post and group records into the EXACT output format requested by the user.\n"
            f"Requested Target Format: {target_format}\n"
            f"User Instructions / Prompt: {custom_instructions or original_prompt or 'Format the records cleanly according to target format.'}\n\n"
            "Formatting Rules:\n"
            "1. Output ONLY the raw formatted result (e.g. valid HTML, valid XML, valid YAML, valid LaTeX, clean Markdown, clean JSON, etc.).\n"
            "2. Do NOT include any conversational introduction, greetings, or explanations.\n"
            "3. If formatting in HTML/XML, ensure tags are properly closed and escaped.\n"
            "4. If formatting in Markdown/HTML/XML, make sure post URLs are rendered as clickable links where applicable."
        )

        user_content = json.dumps({"posts": posts_data, "groups": groups_data}, indent=2, ensure_ascii=False)

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_instruction}\n\nInput Scraped Data (JSON):\n{user_content}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # If wrapped in markdown code blocks, strip them if the target format is HTML/XML/YAML/JSON
            if raw_text.startswith("```") and raw_text.endswith("```"):
                lines = raw_text.split("\n")
                if len(lines) >= 3:
                    raw_text = "\n".join(lines[1:-1]).strip()
            return raw_text

    def format_csv(
        self,
        posts: List[PostPayload],
        group_records: List[GroupRecord],
        columns: Optional[List[str]] = None,
    ) -> str:
        """
        Generate CSV string containing matched posts and gated groups.
        """
        cols = columns or self.DEFAULT_COLUMNS
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(cols)

        # 1. Write matched posts (Requires joining = false)
        for p in posts:
            row = []
            for col in cols:
                val = self._resolve_field(col, post=p, is_gated=False)
                row.append(val)
            writer.writerow(row)

        # 2. Write gated groups (Requires joining = true)
        for g in group_records:
            if g.requires_joining:
                row = []
                for col in cols:
                    val = self._resolve_field(col, group=g, is_gated=True)
                    row.append(val)
                writer.writerow(row)

        return output.getvalue()

    def format_markdown_table(
        self,
        posts: List[PostPayload],
        group_records: List[GroupRecord],
        columns: Optional[List[str]] = None,
    ) -> str:
        """
        Generate GitHub-flavored markdown table.
        """
        cols = columns or [
            "GroupName",
            "Status",
            "Author",
            "Price",
            "Published",
            "Link",
            "Snippet",
        ]
        headers = " | ".join(cols)
        separators = " | ".join(["---"] * len(cols))
        rows = [f"| {headers} |", f"| {separators} |"]

        # Matched posts
        for p in posts:
            vals = []
            for c in cols:
                c_low = c.lower()
                if "group" in c_low:
                    vals.append(p.group_name or "N/A")
                elif "status" in c_low or "join" in c_low:
                    vals.append("✅ Accessible")
                elif "author" in c_low:
                    vals.append(p.author_name or "Unknown")
                elif "price" in c_low:
                    vals.append(f"{p.price} NIS" if p.price is not None else "N/A")
                elif "date" in c_low or "published" in c_low:
                    vals.append(p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "Recent")
                elif "link" in c_low or "url" in c_low:
                    vals.append(f"[Post Link]({p.post_url})" if p.post_url else "N/A")
                elif "snippet" in c_low or "desc" in c_low:
                    clean_text = p.snippet.replace("\n", " ").replace("|", "-")
                    vals.append(clean_text)
                else:
                    vals.append("")
            rows.append(f"| {' | '.join(vals)} |")

        # Gated groups
        for g in group_records:
            if g.requires_joining:
                vals = []
                for c in cols:
                    c_low = c.lower()
                    if "group" in c_low:
                        vals.append(g.group_name)
                    elif "status" in c_low or "join" in c_low:
                        vals.append("🔒 Requires Joining")
                    elif "link" in c_low or "url" in c_low:
                        vals.append(f"[Group Link]({g.group_url})" if g.group_url else "N/A")
                    else:
                        vals.append("-")
                rows.append(f"| {' | '.join(vals)} |")

        return "\n".join(rows)

    def format_html_table(
        self,
        posts: List[PostPayload],
        group_records: List[GroupRecord],
        columns: Optional[List[str]] = None,
    ) -> str:
        """
        Generate clean, responsive HTML table with embedded CSS styling.
        """
        import html
        cols = columns or [
            "GroupName",
            "Status",
            "Author",
            "Price",
            "Published",
            "Link",
            "Snippet",
        ]

        th_cells = "".join(f"<th style='padding: 10px; border: 1px solid #ddd; background-color: #f4f6f8; text-align: left;'>{html.escape(c)}</th>" for c in cols)
        table_rows = []

        # Matched posts
        for p in posts:
            td_cells = []
            for c in cols:
                c_low = c.lower()
                if "group" in c_low:
                    td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{html.escape(p.group_name or 'N/A')}</td>")
                elif "status" in c_low or "join" in c_low:
                    td_cells.append("<td style='padding: 8px; border: 1px solid #ddd; color: green;'>&#x2705; Accessible</td>")
                elif "author" in c_low:
                    td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'><strong>{html.escape(p.author_name or 'Unknown')}</strong></td>")
                elif "price" in c_low:
                    price_val = f"{p.price} NIS" if p.price is not None else "N/A"
                    td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{html.escape(price_val)}</td>")
                elif "date" in c_low or "published" in c_low:
                    date_val = p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "Recent"
                    td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{html.escape(date_val)}</td>")
                elif "link" in c_low or "url" in c_low:
                    if p.post_url:
                        td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'><a href='{html.escape(p.post_url)}' target='_blank' rel='noopener noreferrer'>View Post</a></td>")
                    else:
                        td_cells.append("<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>")
                elif "snippet" in c_low or "desc" in c_low or "content" in c_low:
                    td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd; max-width: 400px; word-wrap: break-word;'>{html.escape(p.snippet or p.content_text)}</td>")
                else:
                    td_cells.append("<td style='padding: 8px; border: 1px solid #ddd;'></td>")
            
            table_rows.append(f"<tr>{''.join(td_cells)}</tr>")

        # Gated groups
        for g in group_records:
            if g.requires_joining:
                td_cells = []
                for c in cols:
                    c_low = c.lower()
                    if "group" in c_low:
                        td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{html.escape(g.group_name)}</td>")
                    elif "status" in c_low or "join" in c_low:
                        td_cells.append("<td style='padding: 8px; border: 1px solid #ddd; color: red;'>&#x1F512; Requires Joining</td>")
                    elif "link" in c_low or "url" in c_low:
                        link_val = f"<a href='{html.escape(g.group_url)}' target='_blank'>View Group</a>" if g.group_url else "N/A"
                        td_cells.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{link_val}</td>")
                    else:
                        td_cells.append("<td style='padding: 8px; border: 1px solid #ddd;'>-</td>")
                table_rows.append(f"<tr>{''.join(td_cells)}</tr>")

        tbody_content = "\n".join(table_rows)
        return (
            "<table style='width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; font-size: 14px;'>\n"
            f"  <thead>\n    <tr>{th_cells}</tr>\n  </thead>\n"
            f"  <tbody>\n{tbody_content}\n  </tbody>\n"
            "</table>"
        )

    def format_mermaid_diagram(
        self, posts: List[PostPayload], group_records: List[GroupRecord]
    ) -> str:
        """
        Generate Mermaid graph diagram representing discovered groups and posts.
        """
        lines = ["flowchart TD", "    Root[Facebook Scrape Target]"]

        # Discovered Groups
        seen_groups = set()
        for idx, g in enumerate(group_records):
            gid = f"G_{idx}"
            seen_groups.add(g.group_name)
            lock_icon = "🔒 " if g.requires_joining else "🌐 "
            lines.append(f"    Root --> {gid}[\"{lock_icon}{g.group_name}\"]")

        for idx, p in enumerate(posts):
            pid = f"P_{idx}"
            grp = p.group_name or "Ungrouped"
            safe_grp = grp.replace('"', '')
            if grp not in seen_groups:
                gid = f"G_post_{idx}"
                seen_groups.add(grp)
                lines.append(f"    Root --> {gid}[\"🌐 {safe_grp}\"]")
            else:
                gid = f"G_post_{idx}"

            author = p.author_name or "Anonymous"
            price_str = f" ({p.price} NIS)" if p.price is not None else ""
            lines.append(f"    {gid} --> {pid}[\"📝 {author}{price_str}\"]")

        return "\n".join(lines)

    def format_json(
        self, posts: List[PostPayload], group_records: List[GroupRecord]
    ) -> str:
        """
        Generate clean JSON dump of results.
        """
        data = {
            "posts": [p.model_dump(mode="json") for p in posts],
            "gated_groups": [g.model_dump(mode="json") for g in group_records if g.requires_joining],
            "total_posts_found": len(posts),
            "total_gated_groups": len([g for g in group_records if g.requires_joining]),
        }
        return json.dumps(data, indent=2, default=str)

    def _resolve_field(
        self,
        col_name: str,
        post: Optional[PostPayload] = None,
        group: Optional[GroupRecord] = None,
        is_gated: bool = False,
    ) -> str:
        """Helper to map flexible column headers to post or group attributes."""
        col_lower = col_name.lower()

        if is_gated:
            if "group" in col_lower:
                return group.group_name if group else ""
            if "join" in col_lower:
                return "true"
            if "link" in col_lower or "url" in col_lower:
                return group.group_url or "" if group else ""
            return ""

        if post:
            if "group" in col_lower:
                return post.group_name or ""
            if "join" in col_lower:
                return "false"
            if "link" in col_lower or "url" in col_lower:
                return post.post_url or ""
            if "date" in col_lower or "publish" in col_lower or "time" in col_lower:
                return post.published_at.strftime("%Y-%m-%d %H:%M") if post.published_at else ""
            if "snippet" in col_lower or "desc" in col_lower or "content" in col_lower:
                return post.snippet or post.content_text
            if "author" in col_lower:
                return post.author_name or ""
            if "price" in col_lower:
                return str(post.price) if post.price is not None else ""

        return ""
