"""Vision Fallback Handler: Calculates relative offsets from bounding boxes for dynamic AI coordinate clicks."""

import os
import json
import base64
from typing import Optional, Callable, Dict, Any, Tuple
from pydantic import BaseModel


class TargetElementLocation(BaseModel):
    target_label: str
    relative_x: int
    relative_y: int
    confidence: float = 1.0


class VisionFallbackHandler:
    """Uses vision AI models to locate visual elements in cropped container screenshots."""

    def __init__(self, ai_detector: Optional[Callable[[bytes, str], Dict[str, Any]]] = None):
        self.ai_detector = ai_detector

    def compute_viewport_coordinates(
        self,
        container_box: Dict[str, float],
        element_location: TargetElementLocation,
    ) -> Tuple[int, int]:
        """
        Translates relative coordinates inside a bounding box crop to absolute viewport coordinates.
        :param container_box: Dict with 'x', 'y', 'width', 'height' of the bounding box.
        :param element_location: Relative x and y offset inside the bounding box.
        :return: (abs_x, abs_y) viewport coordinates ready for page.mouse.click(abs_x, abs_y).
        """
        abs_x = int(container_box["x"] + element_location.relative_x)
        abs_y = int(container_box["y"] + element_location.relative_y)
        return abs_x, abs_y

    def locate_target_in_crop(
        self,
        image_bytes: bytes,
        target_action: str = "expand_see_more",
    ) -> Optional[TargetElementLocation]:
        """
        Invokes vision AI on cropped container screenshot to return relative pixel offset of target.
        """
        if self.ai_detector:
            result = self.ai_detector(image_bytes, target_action)
            return TargetElementLocation.model_validate(result)

        # Fallback to OpenAI vision if OPENAI_API_KEY is configured
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            try:
                return self._call_vision_llm(image_bytes, target_action, openai_key)
            except Exception:
                pass

        return None

    def _call_vision_llm(self, image_bytes: bytes, target_action: str, api_key: str) -> TargetElementLocation:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            f"Analyze this cropped component screenshot. We need to perform action: '{target_action}' "
            "(e.g., clicking 'See more' / 'Show more' / 'Join Group'). "
            "Return a JSON object with: { 'target_label': string, 'relative_x': int, 'relative_y': int, 'confidence': float } "
            "where relative_x and relative_y are the exact pixel coordinates within this cropped image."
        )

        response = client.chat.completions.create(
            model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return TargetElementLocation.model_validate(data)
