import base64
import json
import os
import logging
from dotenv import load_dotenv
from collections import Counter

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical monitoring AI watching an elderly Alzheimer's patient near their medication dispenser. Analyze the image and classify exactly ONE of these states:

TOOK_PILL  - Person is taking or just took their medication. Use this broadly for ANY of:
             * Hand/fingers reaching toward or near the mouth holding a pill
             * Putting a pill in the mouth
             * Chewing or swallowing a pill
             * Drinking water or any liquid (water is used to wash pills down, so drinking during the pill window counts)
             * Holding a cup, glass, or bottle near the mouth
             * Visible pill, tablet, or capsule moving toward the mouth
             * Mouth open while hand is near it, suggesting ingestion

NO_TAKE    - Person is clearly visible, upright, and going about normal activity without any pill-taking gesture. They are awake, alert, and not reaching for pills or water. Use this when the person is simply present and doing nothing medication-related. A person who finished taking their pill and is now just sitting calmly is also NO_TAKE.

DISTRESS   - Reserve this for CLEAR physical emergencies only. Use DISTRESS when you see:
             * Person collapsed or lying on the floor
             * Person slumped unnaturally, head fallen forward or backward, body clearly limp
             * Person falling or in the middle of a fall
             * Person clutching chest/head with a pained expression
             * Body in an obviously abnormal, non-resting posture suggesting medical emergency
             Do NOT use DISTRESS for:
             * A person simply sitting quietly or resting with eyes closed in a normal posture
             * A person who appears calm or relaxed
             * An empty frame or when the person has left
             * Ambiguous situations — prefer NO_TAKE if you are not certain something is medically wrong

NO_SHOW    - No person is visible in the frame. This is NOT distress — the person may have finished and walked away.

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
    """Priority-based classification:

    1. DISTRESS — only if a SIGNIFICANT portion of frames show distress (>=30% AND >=3 frames).
       A single distress frame is likely a misread and will be ignored.
    2. TOOK_PILL — if >=2 high-confidence frames show pill-taking (broad definition including
       drinking water or hand-to-mouth gestures).
    3. Otherwise — majority vote.
    """
    valid = [r for r in frame_results if r is not None]

    if len(valid) < 3:
        return {"state": "NO_TAKE", "confidence": 0.0, "reason": "Insufficient valid frames"}

    # DISTRESS: require significant evidence, not just one frame
    distress_frames = [r for r in valid if r["state"] == "DISTRESS" and r["confidence"] >= 0.7]
    distress_ratio = len(distress_frames) / len(valid)
    if len(distress_frames) >= 3 and distress_ratio >= 0.30:
        avg_conf = sum(r["confidence"] for r in distress_frames) / len(distress_frames)
        return {
            "state": "DISTRESS",
            "confidence": round(avg_conf, 2),
            "reason": f"Detected distress in {len(distress_frames)}/{len(valid)} frames: {distress_frames[0]['reason']}",
        }

    # TOOK_PILL override: if >=2 frames show TOOK_PILL with confidence >=0.7, count it
    took_pill_frames = [r for r in valid if r["state"] == "TOOK_PILL" and r["confidence"] >= 0.7]
    if len(took_pill_frames) >= 2:
        avg_conf = sum(r["confidence"] for r in took_pill_frames) / len(took_pill_frames)
        return {
            "state": "TOOK_PILL",
            "confidence": round(avg_conf, 2),
            "reason": f"Detected pill-taking in {len(took_pill_frames)}/{len(valid)} frames: {took_pill_frames[0]['reason']}",
        }

    # Otherwise, majority vote (excluding DISTRESS since we already rejected it above)
    non_distress = [r for r in valid if r["state"] != "DISTRESS"]
    pool = non_distress if non_distress else valid
    states = [r["state"] for r in pool]
    winner = Counter(states).most_common(1)[0][0]
    winning_results = [r for r in pool if r["state"] == winner]
    avg_confidence = sum(r["confidence"] for r in winning_results) / len(winning_results)

    return {
        "state": winner,
        "confidence": round(avg_confidence, 2),
        "reason": winning_results[0]["reason"],
    }
