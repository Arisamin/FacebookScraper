"""TDD Unit Tests for Task Compiler (Natural Language -> TaskManifest)."""

import pytest
from src.models.manifest import (
    TaskManifest,
    TargetType,
    OutputFormat,
    ActionType,
)
from src.compiler.task_compiler import TaskCompiler


class TestTaskCompiler:
    """Test suite verifying compilation of human language prompts into TaskManifest."""

    def test_compile_empty_prompt_raises_error(self):
        compiler = TaskCompiler()
        with pytest.raises(ValueError, match="cannot be empty"):
            compiler.compile("")

        with pytest.raises(ValueError, match="cannot be empty"):
            compiler.compile("   ")

    def test_compile_furniture_group_search(self):
        """Verify the specific furniture buyer search query."""
        prompt = (
            "search in all groups including the word 'furniture' in their name, "
            "and find posts from the last month in Israel, in which people are asking to buy used furniture. "
            "I want the output to be in a csv file with the following columns: "
            "GroupName | Requires joining (true/false)| post link | date of publish | description snippet (up to 40 words). "
            "If a group does not allow seeing the posts in it without first joining then I expect it to have an "
            "entry with the group name and 'Requires joining' set to true."
        )

        compiler = TaskCompiler()
        manifest: TaskManifest = compiler.compile(prompt)

        assert isinstance(manifest, TaskManifest)
        assert manifest.target.type == TargetType.GROUP_SEARCH
        assert "furniture" in manifest.target.url_or_query.lower()
        assert manifest.target.location is not None and "israel" in manifest.target.location.lower()
        assert manifest.criteria.timeframe_days == 30
        assert manifest.criteria.intent == "buyer_request"
        assert manifest.output_config.format == OutputFormat.CSV
        assert manifest.output_config.columns is not None
        assert len(manifest.output_config.columns) == 5
        assert any("group" in col.lower() for col in manifest.output_config.columns)
        assert any("join" in col.lower() for col in manifest.output_config.columns)
        assert manifest.output_config.snippet_max_words == 40
        assert manifest.privacy_handling.record_gated_groups is True

    def test_compile_apartment_rental_query(self):
        """Verify direct group URL scraping with negative keywords and Telegram action."""
        prompt = (
            "Find 2-3 room apartments under 6500 NIS in https://facebook.com/groups/telavivrentals, "
            "ignore roommates and sublets, output as a markdown table and send telegram alert to 987654321"
        )

        compiler = TaskCompiler()
        manifest: TaskManifest = compiler.compile(prompt)

        assert manifest.target.type == TargetType.GROUP
        assert "facebook.com/groups/telavivrentals" in manifest.target.url_or_query
        assert manifest.criteria.price_max == 6500.0
        assert any("roommate" in kw.lower() for kw in manifest.criteria.exclude_keywords)
        assert manifest.output_config.format == OutputFormat.MARKDOWN_TABLE
        assert len(manifest.actions) == 1
        assert manifest.actions[0].type == ActionType.TELEGRAM
        assert manifest.actions[0].target_config.get("channel_id") == "987654321"

    def test_compile_marketplace_car_search(self):
        """Verify marketplace target with price ceiling and json export."""
        prompt = "Search marketplace for Toyota Corolla under 45000 NIS in Jerusalem, export to json file"

        compiler = TaskCompiler()
        manifest: TaskManifest = compiler.compile(prompt)

        assert manifest.target.type == TargetType.MARKETPLACE
        assert "toyota corolla" in manifest.target.url_or_query.lower()
        assert manifest.target.location is not None and "jerusalem" in manifest.target.location.lower()
        assert manifest.criteria.price_max == 45000.0
        assert manifest.output_config.format == OutputFormat.JSON

    def test_custom_llm_handler_injection(self):
        """Verify that a custom LLM handler can be injected for mocking."""
        mock_response = {
            "task_id": "custom_mock_task",
            "description": "mock prompt",
            "target": {
                "type": "page",
                "url_or_query": "https://facebook.com/MyBrandPage",
                "max_posts_to_scan": 15,
                "max_scrolls": 5,
            },
            "criteria": {
                "include_keywords": ["discount", "sale"],
                "exclude_keywords": [],
            },
            "output_config": {
                "format": "executive_summary",
            },
            "privacy_handling": {
                "record_gated_groups": False,
            },
            "actions": [],
        }

        compiler = TaskCompiler(llm_client=lambda prompt: mock_response)
        manifest = compiler.compile("Summarize discounts on MyBrandPage")

        assert manifest.task_id == "custom_mock_task"
        assert manifest.target.type == TargetType.PAGE
        assert manifest.target.url_or_query == "https://facebook.com/MyBrandPage"
        assert manifest.output_config.format == OutputFormat.EXECUTIVE_SUMMARY
