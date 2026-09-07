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

        # Fallback to Google Gemini Vision if GEMINI_API_KEY is configured
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                return self._call_gemini_vision(image_bytes, target_action, gemini_key)
            except Exception:
                pass

        return None

    def _call_gemini_vision(self, image_bytes: bytes, target_action: str, api_key: str) -> TargetElementLocation:
        import urllib.request
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        prompt = (
            f"Analyze this cropped component screenshot. We need to perform action: '{target_action}' "
            "(e.g., clicking 'See more' / 'Show more' / 'Join Group'). "
            "Return a JSON object with: { \"target_label\": string, \"relative_x\": int, \"relative_y\": int, \"confidence\": float } "
            "where relative_x and relative_y are the exact pixel coordinates within this cropped image."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            res_dict = json.loads(raw_text)
            return TargetElementLocation.model_validate(res_dict)
