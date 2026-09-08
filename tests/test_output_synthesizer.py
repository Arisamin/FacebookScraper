"""Unit tests for Output Synthesizer (CSV, Markdown Tables, Mermaid Diagrams, JSON)."""

import pytest
from datetime import datetime
from src.models.post import PostPayload, GroupRecord
from src.synthesizer.formatters import OutputSynthesizer


class TestOutputSynthesizer:
    """Test suite for transforming scraped posts and gated group records into requested formats."""

    @pytest.fixture
    def sample_data(self):
        posts = [
            PostPayload(
                post_id="p101",
                group_name="Furniture Buy & Sell Israel",
                author_name="Noa Bar",
                published_at=datetime(2025, 2, 10, 14, 0),
                content_text="Looking for a vintage sofa in good condition.",
                snippet="Looking for a vintage sofa in good condition.",
                price=800.0,
                post_url="https://facebook.com/groups/furniture/posts/101",
                requires_joining=False,
            )
        ]
        group_records = [
            GroupRecord(
                group_name="Secret Antique Furniture Club",
                group_url="https://facebook.com/groups/secretantique",
                requires_joining=True,
                is_accessible=False,
            )
        ]
        return posts, group_records

    def test_format_csv_with_exact_custom_columns(self, sample_data):
        posts, group_records = sample_data
        synthesizer = OutputSynthesizer()

        custom_columns = [
            "GroupName",
            "Requires joining (true/false)",
            "post link",
            "date of publish",
            "description snippet (up to 40 words)",
        ]

        csv_output = synthesizer.format_csv(posts, group_records, columns=custom_columns)

        lines = [line.strip() for line in csv_output.strip().split("\n") if line.strip()]
        assert len(lines) == 3  # Header + 1 post + 1 gated group

        # Verify Header
        assert "GroupName,Requires joining (true/false),post link,date of publish,description snippet (up to 40 words)" in lines[0]

        # Verify Post row
        assert "Furniture Buy & Sell Israel,false,https://facebook.com/groups/furniture/posts/101" in lines[1]
        assert "Looking for a vintage sofa" in lines[1]

        # Verify Gated Group row
        assert "Secret Antique Furniture Club,true" in lines[2]

    def test_format_markdown_table(self, sample_data):
        posts, group_records = sample_data
        synthesizer = OutputSynthesizer()

        md_output = synthesizer.format_markdown_table(posts, group_records)

        assert "| Group Name |" in md_output or "| GroupName |" in md_output
        assert "| Furniture Buy & Sell Israel |" in md_output
        assert "| Secret Antique Furniture Club |" in md_output
        assert "🔒 Requires Joining" in md_output or "true" in md_output.lower()

    def test_format_mermaid_diagram(self, sample_data):
        posts, group_records = sample_data
        synthesizer = OutputSynthesizer()

        mermaid = synthesizer.format_mermaid_diagram(posts, group_records)

        assert "graph TD" in mermaid or "flowchart TD" in mermaid
        assert "Furniture Buy & Sell Israel" in mermaid
        assert "Secret Antique Furniture Club" in mermaid
        assert "Noa Bar" in mermaid

    def test_format_json(self, sample_data):
        posts, group_records = sample_data
        synthesizer = OutputSynthesizer()

        json_str = synthesizer.format_json(posts, group_records)
        assert '"posts"' in json_str
        assert '"gated_groups"' in json_str
        assert "p101" in json_str

    def test_format_html_table(self, sample_data):
        posts, group_records = sample_data
        synthesizer = OutputSynthesizer()

        html_out = synthesizer.format_html_table(posts, group_records)
        assert "<table" in html_out
        assert "<thead>" in html_out
        assert "<tbody>" in html_out
        assert "Furniture Buy &amp; Sell Israel" in html_out or "Furniture Buy & Sell Israel" in html_out
        assert "Noa Bar" in html_out
        assert "Secret Antique Furniture Club" in html_out
        assert "Requires Joining" in html_out

