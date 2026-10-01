import json
import logging
import re
from typing import List

from app.config import get_settings
from app.models import PanelOutline


logger = logging.getLogger(__name__)


def extract_json(text: str):

    if not text:
        raise ValueError(
            "Empty model response."
        )

    text = text.strip()

    fenced = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if fenced:
        text = fenced.group(1).strip()

    start = text.find("[")

    end = text.rfind("]")

    if start == -1 or end == -1:
        raise ValueError(
            "Could not find JSON array."
        )

    return json.loads(
        text[start:end + 1]
    )


def fallback_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> List[PanelOutline]:

    scenes = [
        (
            "The Beginning",
            f"{character_name} begins an adventure "
            f"in the {setting}."
        ),
        (
            "A Strange Discovery",
            f"{character_name} discovers "
            f"something connected to "
            f"the mission: {story_prompt}."
        ),
        (
            "Trouble Arrives",
            f"An unexpected obstacle "
            f"interrupts the adventure."
        ),
        (
            "The Clever Solution",
            f"{character_name} finds a creative "
            f"way to overcome the obstacle."
        ),
        (
            "A New Beginning",
            f"The adventure ends with a "
            f"{tone.lower()} new possibility."
        ),
    ]

    panels = []

    for index, (title, scene) in enumerate(
        scenes,
        start=1,
    ):

        panels.append(
            PanelOutline(
                panel=index,
                title=title,
                scene_description=scene,
                image_prompt=(
                    f"{art_style} comic panel. "
                    f"Same character throughout: "
                    f"{character_name}. "
                    f"Setting: {setting}. "
                    f"{scene}"
                ),
            )
        )

    return panels


def generate_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> List[PanelOutline]:

    settings = get_settings()

    if not settings.gemini_api_key:

        logger.warning(
            "Gemini API key is not configured. "
            "Using fallback outline."
        )

        return fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
        )

    try:

        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=settings.gemini_api_key
        )

        prompt = f"""
You are an expert comic-book story planner.

Create exactly FIVE sequential comic panels.

USER STORY:
{story_prompt}

MAIN CHARACTER:
{character_name}

SETTING:
{setting}

TONE:
{tone}

ART STYLE:
{art_style}

Requirements:

1. Exactly five panels.
2. Maintain character continuity.
3. Maintain setting continuity.
4. Each panel must move the story forward.
5. Give each panel a short title.
6. Give a concise scene description.
7. Give a detailed image-generation prompt.

Return ONLY JSON.

Format:

[
  {{
    "panel": 1,
    "title": "...",
    "scene_description": "...",
    "image_prompt": "..."
  }}
]
"""

        response = client.models.generate_content(
            model=settings.gemini_flash_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        raw = extract_json(
            response.text
        )

        if not isinstance(raw, list):
            raise ValueError(
                "Gemini response is not a list."
            )

        if len(raw) < 5:
            raise ValueError(
                "Gemini returned fewer than "
                "five panels."
            )

        panels = []

        for index, item in enumerate(
            raw[:5],
            start=1,
        ):

            panels.append(
                PanelOutline(
                    panel=index,
                    title=str(
                        item.get(
                            "title",
                            f"Panel {index}",
                        )
                    ),
                    scene_description=str(
                        item.get(
                            "scene_description",
                            "",
                        )
                    ),
                    image_prompt=str(
                        item.get(
                            "image_prompt",
                            "",
                        )
                    ),
                )
            )

        return panels

    except Exception as exc:

        logger.exception(
            "Gemini Flash failed: %s",
            exc,
        )

        return fallback_outline(
            story_prompt,
            character_name,
            setting,
            tone,
            art_style,
        )