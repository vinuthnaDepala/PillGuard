import base64
import json
import os
import logging
from dotenv import load_dotenv
from collections import Counter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical monitoring AI watching an elderly Alzheimer's patient take their medication.
Analyze the image and classify exactly ONE of these states:

TOOK_PILL  - Person is clearly drinking, swallowing, or has pill/medicine moving toward mouth
NO_TAKE    - Person is present but not taking medication
DISTRESS   - Person has fallen, collapsed, is on the floor, or appears in physical distress
NO_SHOW    - No person visible in frame

Respond ONLY with a JSON object, no other text:
{
  "state": "TOOK_PILL" | "NO_TAKE" | "DISTRESS" | "NO_SHOW",
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation"
}"""


def _detect_media_type(image_path):
    with open(image_path, "rb") as f:
        header = f.read(8)
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    elif header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    else:
        return "image/png"


def classify_frame(image_path):
    """Send a single frame to Claude Vision API and return classification."""
    import anthropic

    try:
        media_type = _detect_media_type(image_path)

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Classify this frame.",
                        },
                    ],
                }
            ],
        )

        result_text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            result_text = "\n".join(lines)

        result = json.loads(result_text)
        return result

    except Exception as e:
        logger.error(f"Claude Vision classification failed: {e}")
        return None


def final_classification(frame_results):
    """Majority vote with DISTRESS override."""
    valid = [r for r in frame_results if r is not None]

    if len(valid) < 3:
        return {"state": "NO_TAKE", "confidence": 0.0, "reason": "Insufficient valid frames"}

    if any(r["state"] == "DISTRESS" for r in valid):
        distress = next(r for r in valid if r["state"] == "DISTRESS")
        return {
            "state": "DISTRESS",
            "confidence": distress["confidence"],
            "reason": distress["reason"],
        }

    states = [r["state"] for r in valid]
    winner = Counter(states).most_common(1)[0][0]
    winning_results = [r for r in valid if r["state"] == winner]
    avg_confidence = sum(r["confidence"] for r in winning_results) / len(winning_results)

    return {
        "state": winner,
        "confidence": round(avg_confidence, 2),
        "reason": winning_results[0]["reason"],
    }
