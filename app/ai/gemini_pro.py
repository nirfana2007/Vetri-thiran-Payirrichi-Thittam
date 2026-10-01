import json
import logging
import re
from typing import List

from app.config import get_settings
from app.models import (
    ComicPanel,
    PanelOutline,
)


logger = logging.getLogger(__name__)


def extract_json(text: str):

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
            "JSON array not found."
        )

    return json.loads(
        text[start:end + 1]
    )


def fallback_script(
    outline: List[PanelOutline],
    character_name: str,
) -> List[ComicPanel]:

    captions = [
        "THE ADVENTURE BEGINS!",
        "SOMETHING IS WRONG!",
        "LOOK OUT!",
        "A CLEVER IDEA!",
        "UNTIL THE NEXT ADVENTURE...",
    ]

    dialogue = [
        f'{character_name}: "This is going to be amazing!"',
        f'{character_name}: "Wait... what is that?"',
        f'{character_name}: "We have to keep moving!"',
        f'{character_name}: "I know what we can do!"',
        f'{character_name}: "We did it!"',
    ]

    panels = []

    for index, item in enumerate(
        outline[:5]
    ):

        panels.append(
            ComicPanel(
                panel=item.panel,
                title=item.title,
                scene_description=item.scene_description,
                image_prompt=item.image_prompt,
                narration=(
                    item.scene_description
                ),
                dialogue=dialogue[index],
                caption=captions[index],
            )
        )

    return panels


def generate_script(
    outline: List[PanelOutline],
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> List[ComicPanel]:

    settings = get_settings()

    if not settings.gemini_api_key:

        return fallback_script(
            outline,
            character_name,
        )

    try:

        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=settings.gemini_api_key
        )

        prompt = f"""
You are an expert comic-book script writer.

Expand this five-panel outline.

Character:
{character_name}

Setting:
{setting}

Tone:
{tone}

Art style:
{art_style}

OUTLINE:
{json.dumps(
    [x.model_dump() for x in outline],
    ensure_ascii=False,
)}

Return ONLY JSON.

Exactly five objects.

Each object must contain:

panel
title
scene_description
image_prompt
narration
dialogue
caption

Dialogue format:

Character: "dialogue"

Keep the character visually consistent.
Keep the story continuous.
"""

        response = client.models.generate_content(
            model=settings.gemini_pro_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.75,
                response_mime_type="application/json",
            ),
        )

        raw = extract_json(
            response.text
        )

        if len(raw) < 5:
            raise ValueError(
                "Gemini Pro returned fewer than "
                "five panels."
            )

        panels = []

        for index, item in enumerate(
            raw[:5],
            start=1,
        ):

            original = outline[index - 1]

            panels.append(
                ComicPanel(
                    panel=index,
                    title=str(
                        item.get(
                            "title",
                            original.title,
                        )
                    ),
                    scene_description=str(
                        item.get(
                            "scene_description",
                            original.scene_description,
                        )
                    ),
                    image_prompt=str(
                        item.get(
                            "image_prompt",
                            original.image_prompt,
                        )
                    ),
                    narration=str(
                        item.get(
                            "narration",
                            original.scene_description,
                        )
                    ),
                    dialogue=str(
                        item.get(
                            "dialogue",
                            f'{character_name}: "Let\'s go!"',
                        )
                    ),
                    caption=str(
                        item.get(
                            "caption",
                            f"PANEL {index}",
                        )
                    ),
                )
            )

        return panels

    except Exception as exc:

        logger.exception(
            "Gemini Pro failed: %s",
            exc,
        )

        return fallback_script(
            outline,
            character_name,
        )