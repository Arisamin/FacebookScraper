"""Unit tests for AI Vision Fallback and Coordinate Inferrer."""

import pytest
from unittest.mock import MagicMock
from src.scraper.vision_fallback import VisionFallbackHandler, TargetElementLocation


class TestVisionFallbackHandler:
    """Test suite verifying AI coordinate calculation for dynamic recovery."""

    def test_calculate_absolute_coordinates_from_bounding_box(self):
        handler = VisionFallbackHandler()

        # Suppose the container/post element has viewport bounding box:
        # x=100, y=250, width=500, height=300
        box = {"x": 100, "y": 250, "width": 500, "height": 300}

        # Suppose AI detects the "See more" text button at relative offset:
        # rel_x=420, rel_y=280 inside that 500x300 image
        loc = TargetElementLocation(
            target_label="See more",
            relative_x=420,
            relative_y=280,
            confidence=0.95,
        )

        abs_x, abs_y = handler.compute_viewport_coordinates(box, loc)
        assert abs_x == 520  # 100 + 420
        assert abs_y == 530  # 250 + 280

    def test_mock_vision_ai_detection(self):
        """Test mock vision AI prompt returning target coordinates."""
        mock_ai_response = {
            "target_label": "See more",
            "relative_x": 350,
            "relative_y": 120,
            "confidence": 0.98,
        }

        handler = VisionFallbackHandler(ai_detector=lambda img_bytes, action: mock_ai_response)
        loc = handler.locate_target_in_crop(b"fake_image_bytes", target_action="expand_see_more")

        assert loc is not None
        assert loc.target_label == "See more"
        assert loc.relative_x == 350
        assert loc.relative_y == 120
