import logging
import time
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings


logger = logging.getLogger(__name__)


# ============================================================
# FONT HELPERS
# ============================================================

def get_font(size: int, bold: bool = False):
    """
    Try to find a usable system font.

    ComicCraft should still work if a particular font
    is not installed.
    """

    candidates = []

    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for font_path in candidates:

        path = Path(font_path)

        if path.exists():

            try:
                return ImageFont.truetype(
                    str(path),
                    size,
                )
            except Exception:
                pass

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
):
    """
    Wrap text so that it fits inside a specified width.
    """

    if not text:
        return []

    words = text.split()

    lines = []

    current_line = ""

    for word in words:

        test_line = (
            f"{current_line} {word}".strip()
        )

        bbox = draw.textbbox(
            (0, 0),
            test_line,
            font=font,
        )

        width = bbox[2] - bbox[0]

        if (
            width <= max_width
            or not current_line
        ):

            current_line = test_line

        else:

            lines.append(current_line)

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


# ============================================================
# FALLBACK IMAGE GENERATOR
# ============================================================

def create_fallback_image(
    prompt: str,
    panel_number: int,
    art_style: str,
) -> str:
    """
    Creates a placeholder comic panel when an external
    image-generation API is unavailable.

    This makes the application usable even without
    HF_API_KEY.
    """

    settings = get_settings()

    width = 1024
    height = 1024

    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # Comic border
    # --------------------------------------------------------

    border_width = 18

    draw.rectangle(
        (
            border_width,
            border_width,
            width - border_width,
            height - border_width,
        ),
        outline="black",
        width=border_width,
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    title_font = get_font(
        52,
        bold=True,
    )

    body_font = get_font(
        30,
        bold=False,
    )

    small_font = get_font(
        24,
        bold=False,
    )

    draw.text(
        (60, 55),
        f"PANEL {panel_number}",
        fill="black",
        font=title_font,
    )

    # --------------------------------------------------------
    # Comic illustration placeholder
    # --------------------------------------------------------

    center_x = width // 2
    center_y = 470

    # Sun / light source

    draw.ellipse(
        (
            center_x - 100,
            center_y - 100,
            center_x + 100,
            center_y + 100,
        ),
        outline="black",
        width=8,
    )

    # Character head

    head_radius = 105

    draw.ellipse(
        (
            center_x - head_radius,
            center_y - head_radius,
            center_x + head_radius,
            center_y + head_radius,
        ),
        outline="black",
        width=8,
    )

    # Eyes

    eye_y = center_y - 20

    draw.ellipse(
        (
            center_x - 55,
            eye_y - 15,
            center_x - 25,
            eye_y + 15,
        ),
        fill="black",
    )

    draw.ellipse(
        (
            center_x + 25,
            eye_y - 15,
            center_x + 55,
            eye_y + 15,
        ),
        fill="black",
    )

    # Smile

    draw.arc(
        (
            center_x - 50,
            center_y + 10,
            center_x + 50,
            center_y + 80,
        ),
        start=10,
        end=170,
        fill="black",
        width=6,
    )

    # Body

    draw.rectangle(
        (
            center_x - 100,
            center_y + 105,
            center_x + 100,
            center_y + 310,
        ),
        outline="black",
        width=8,
    )

    # --------------------------------------------------------
    # Story prompt
    # --------------------------------------------------------

    prompt_text = (
        prompt[:500]
        if prompt
        else "AI comic panel"
    )

    lines = wrap_text(
        draw,
        prompt_text,
        body_font,
        width - 140,
    )

    y = 690

    for line in lines[:6]:

        draw.text(
            (70, y),
            line,
            fill="black",
            font=body_font,
        )

        y += 42

    # --------------------------------------------------------
    # Style label
    # --------------------------------------------------------

    style_text = (
        f"Style: {art_style}"
    )

    draw.text(
        (70, 940),
        style_text,
        fill="black",
        font=small_font,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    filename = (
        f"panel_{panel_number}_"
        f"{int(time.time() * 1000)}.png"
    )

    output_path = (
        settings.panels_dir / filename
    )

    image.save(
        output_path,
        format="PNG",
    )

    logger.info(
        "Fallback image created: %s",
        output_path,
    )

    return str(
        output_path
    )


# ============================================================
# HUGGING FACE IMAGE GENERATOR
# ============================================================

def generate_huggingface_image(
    prompt: str,
    output_path: Path,
) -> Optional[str]:
    """
    Generate an image using Hugging Face inference.

    Returns the saved image path on success.

    Returns None on failure so the caller can use
    the fallback generator.
    """

    settings = get_settings()

    if not settings.hf_api_key:

        logger.warning(
            "HF_API_KEY is not configured."
        )

        return None

    if not settings.hf_model_id:

        logger.warning(
            "HF_MODEL_ID is not configured."
        )

        return None

    url = (
        "https://router.huggingface.co/"
        "hf-inference/models/"
        f"{settings.hf_model_id}"
    )

    headers = {
        "Authorization":
            f"Bearer {settings.hf_api_key}",
        "Content-Type":
            "application/json",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "num_inference_steps":
                settings.diffusion_steps,
        },
    }

    logger.info(
        "Sending image-generation request "
        "to Hugging Face."
    )

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.hf_timeout_seconds,
        )

        # ----------------------------------------------------
        # Successful response
        # ----------------------------------------------------

        if response.status_code == 200:

            content_type = (
                response.headers
                .get(
                    "content-type",
                    "",
                )
                .lower()
            )

            if (
                "image" not in content_type
            ):

                logger.error(
                    "Hugging Face returned "
                    "non-image content."
                )

                logger.error(
                    response.text[:1000]
                )

                return None

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                output_path,
                "wb",
            ) as file:

                file.write(
                    response.content
                )

            # ------------------------------------------------
            # Verify generated image
            # ------------------------------------------------

            try:

                with Image.open(
                    output_path
                ) as generated_image:

                    generated_image.verify()

            except Exception:

                logger.exception(
                    "Generated file is "
                    "not a valid image."
                )

                try:
                    output_path.unlink()
                except Exception:
                    pass

                return None

            logger.info(
                "Hugging Face image saved: %s",
                output_path,
            )

            return str(output_path)

        # ----------------------------------------------------
        # Model loading / temporary errors
        # ----------------------------------------------------

        logger.error(
            "Hugging Face returned HTTP %s",
            response.status_code,
        )

        try:

            logger.error(
                response.text[:2000]
            )

        except Exception:
            pass

        return None

    except requests.Timeout:

        logger.error(
            "Hugging Face request timed out."
        )

        return None

    except requests.RequestException as exc:

        logger.error(
            "Hugging Face request failed: %s",
            exc,
        )

        return None

    except Exception as exc:

        logger.exception(
            "Unexpected image generation error: %s",
            exc,
        )

        return None


# ============================================================
# MAIN IMAGE GENERATOR
# ============================================================

def generate_image(
    prompt: str,
    panel_number: int,
    art_style: str = "Comic Book",
) -> str:
    """
    Main image-generation function used by routes.py.

    Pipeline:

        Comic prompt
             |
             v
        Hugging Face
             |
        success? ---- yes ---> save image
             |
             no
             |
             v
        fallback image
    """

    settings = get_settings()

    if not prompt:
        prompt = (
            "A detailed comic-book scene"
        )

    # --------------------------------------------------------
    # Improve the prompt for image generation
    # --------------------------------------------------------

    enhanced_prompt = f"""
Create a single comic-book illustration.

Art style:
{art_style}

Scene:
{prompt}

Requirements:

- cinematic composition
- clear main subject
- expressive character
- strong visual storytelling
- detailed environment
- consistent character appearance
- clean comic-book artwork
- no watermark
- no random text
- no speech bubbles
- no panel borders
- high quality
"""

    filename = (
        f"panel_{panel_number}_"
        f"{int(time.time() * 1000)}.png"
    )

    output_path = (
        settings.panels_dir / filename
    )

    # --------------------------------------------------------
    # Try Hugging Face
    # --------------------------------------------------------

    generated = generate_huggingface_image(
        prompt=enhanced_prompt,
        output_path=output_path,
    )

    if generated:

        return generated

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    logger.warning(
        "Using fallback image for panel %s.",
        panel_number,
    )

    return create_fallback_image(
        prompt=prompt,
        panel_number=panel_number,
        art_style=art_style,
    )