"""Output Synthesizer: Formats scraped posts and gated group records into CSV, Markdown, Diagrams, and JSON."""

import io
import csv
import json
from typing import List, Optional, Dict, Any
from src.models.post import PostPayload, GroupRecord


class OutputSynthesizer:
    """Transforms scraped data structures into various user-requested formats."""

    DEFAULT_COLUMNS = [
        "GroupName",
        "Requires joining (true/false)",
        "post link",
        "date of publish",
        "description snippet (up to 40 words)",
    ]

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
