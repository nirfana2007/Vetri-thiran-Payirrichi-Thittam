import logging
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings
from app.models import ComicPanel


logger = logging.getLogger(__name__)


# ============================================================
# FONT HELPER
# ============================================================

def get_font(
    size: int,
    bold: bool = False,
):
    """
    Load a system font.

    Works on Windows and Linux.
    Falls back to Pillow's default font if necessary.
    """

    if bold:

        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]

    else:

        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
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
                continue

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
) -> List[str]:
    """
    Wrap text according to the available pixel width.
    """

    if not text:
        return []

    words = text.split()

    lines = []

    current = ""

    for word in words:

        candidate = (
            f"{current} {word}".strip()
        )

        bbox = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )

        width = (
            bbox[2] - bbox[0]
        )

        if (
            width <= max_width
            or not current
        ):

            current = candidate

        else:

            lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ============================================================
# DRAW SPEECH BUBBLE
# ============================================================

def draw_speech_bubble(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    width: int,
    height: int,
):
    """
    Draw a comic-style speech bubble.
    """

    draw = ImageDraw.Draw(
        canvas
    )

    font = get_font(
        25,
        bold=False,
    )

    padding = 18

    # --------------------------------------------------------
    # Bubble
    # --------------------------------------------------------

    draw.rounded_rectangle(
        (
            x,
            y,
            x + width,
            y + height,
        ),
        radius=30,
        fill="white",
        outline="black",
        width=5,
    )

    # --------------------------------------------------------
    # Bubble tail
    # --------------------------------------------------------

    tail_x = x + 55

    tail_y = y + height

    draw.polygon(
        [
            (
                tail_x,
                tail_y - 2,
            ),
            (
                tail_x + 18,
                tail_y + 40,
            ),
            (
                tail_x + 55,
                tail_y - 2,
            ),
        ],
        fill="white",
        outline="black",
    )

    # --------------------------------------------------------
    # Text
    # --------------------------------------------------------

    lines = wrap_text(
        draw=draw,
        text=text,
        font=font,
        max_width=width - (
            padding * 2
        ),
    )

    text_y = (
        y + padding
    )

    line_height = 34

    for line in lines[:5]:

        draw.text(
            (
                x + padding,
                text_y,
            ),
            line,
            fill="black",
            font=font,
        )

        text_y += line_height


# ============================================================
# DRAW CAPTION
# ============================================================

def draw_caption(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    width: int,
):
    """
    Draw a comic caption box.
    """

    if not text:
        return

    draw = ImageDraw.Draw(
        canvas
    )

    font = get_font(
        24,
        bold=True,
    )

    padding = 14

    lines = wrap_text(
        draw=draw,
        text=text,
        font=font,
        max_width=width - (
            padding * 2
        ),
    )

    line_height = 32

    box_height = max(
        55,
        len(lines) * line_height
        + padding * 2,
    )

    # --------------------------------------------------------
    # Caption background
    # --------------------------------------------------------

    draw.rectangle(
        (
            x,
            y,
            x + width,
            y + box_height,
        ),
        fill="white",
        outline="black",
        width=4,
    )

    # --------------------------------------------------------
    # Caption text
    # --------------------------------------------------------

    text_y = (
        y + padding
    )

    for line in lines:

        draw.text(
            (
                x + padding,
                text_y,
            ),
            line,
            fill="black",
            font=font,
        )

        text_y += line_height


# ============================================================
# LOAD PANEL IMAGE
# ============================================================

def load_panel_image(
    panel: ComicPanel,
    width: int,
    height: int,
) -> Image.Image:
    """
    Load and resize an AI-generated panel image.

    If the image is unavailable, create a placeholder.
    """

    image_path = (
        Path(panel.image_path)
        if panel.image_path
        else None
    )

    if (
        image_path
        and image_path.exists()
    ):

        try:

            image = Image.open(
                image_path
            ).convert("RGB")

            return crop_to_fit(
                image,
                width,
                height,
            )

        except Exception as exc:

            logger.warning(
                "Could not load panel image "
                "%s: %s",
                image_path,
                exc,
            )

    # --------------------------------------------------------
    # Placeholder
    # --------------------------------------------------------

    placeholder = Image.new(
        "RGB",
        (
            width,
            height,
        ),
        "white",
    )

    draw = ImageDraw.Draw(
        placeholder
    )

    font = get_font(
        35,
        bold=True,
    )

    text = (
        f"PANEL {panel.panel}\n\n"
        "Image unavailable"
    )

    lines = text.split("\n")

    y = (
        height // 2
        - len(lines) * 25
    )

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font,
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        draw.text(
            (
                (width - text_width)
                // 2,
                y,
            ),
            line,
            fill="black",
            font=font,
        )

        y += 55

    return placeholder


# ============================================================
# CROP IMAGE TO FIT
# ============================================================

def crop_to_fit(
    image: Image.Image,
    target_width: int,
    target_height: int,
) -> Image.Image:
    """
    Resize an image while preserving aspect ratio,
    then center-crop it.
    """

    source_width, source_height = (
        image.size
    )

    target_ratio = (
        target_width
        / target_height
    )

    source_ratio = (
        source_width
        / source_height
    )

    # --------------------------------------------------------
    # Resize
    # --------------------------------------------------------

    if source_ratio > target_ratio:

        # Source is wider.

        new_height = target_height

        new_width = int(
            source_width
            * target_height
            / source_height
        )

    else:

        # Source is taller.

        new_width = target_width

        new_height = int(
            source_height
            * target_width
            / source_width
        )

    resized = image.resize(
        (
            new_width,
            new_height,
        ),
        Image.Resampling.LANCZOS,
    )

    # --------------------------------------------------------
    # Center crop
    # --------------------------------------------------------

    left = (
        new_width - target_width
    ) // 2

    top = (
        new_height - target_height
    ) // 2

    right = (
        left + target_width
    )

    bottom = (
        top + target_height
    )

    return resized.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )


# ============================================================
# BUILD SINGLE PANEL
# ============================================================

def build_panel(
    panel: ComicPanel,
    panel_width: int = 1000,
    panel_height: int = 900,
) -> Image.Image:
    """
    Build one finished comic panel.

    Contains:

    - AI artwork
    - panel number
    - title
    - caption
    - dialogue bubble
    """

    # --------------------------------------------------------
    # Canvas
    # --------------------------------------------------------

    canvas = Image.new(
        "RGB",
        (
            panel_width,
            panel_height,
        ),
        "white",
    )

    draw = ImageDraw.Draw(
        canvas
    )

    # --------------------------------------------------------
    # Artwork area
    # --------------------------------------------------------

    artwork_height = (
        panel_height - 170
    )

    artwork = load_panel_image(
        panel,
        panel_width,
        artwork_height,
    )

    canvas.paste(
        artwork,
        (
            0,
            0,
        ),
    )

    # --------------------------------------------------------
    # Outer border
    # --------------------------------------------------------

    draw.rectangle(
        (
            4,
            4,
            panel_width - 4,
            panel_height - 4,
        ),
        outline="black",
        width=8,
    )

    # --------------------------------------------------------
    # Panel number
    # --------------------------------------------------------

    number_font = get_font(
        30,
        bold=True,
    )

    draw.rectangle(
        (
            20,
            20,
            130,
            75,
        ),
        fill="white",
        outline="black",
        width=4,
    )

    draw.text(
        (
            42,
            30,
        ),
        f"#{panel.panel}",
        fill="black",
        font=number_font,
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_font = get_font(
        34,
        bold=True,
    )

    title = (
        panel.title
        or f"Panel {panel.panel}"
    )

    title_lines = wrap_text(
        draw,
        title,
        title_font,
        panel_width - 300,
    )

    title_y = 25

    for line in title_lines[:2]:

        draw.text(
            (
                160,
                title_y,
            ),
            line,
            fill="black",
            font=title_font,
        )

        title_y += 40

    # --------------------------------------------------------
    # Dialogue bubble
    # --------------------------------------------------------

    if panel.dialogue:

        bubble_width = 450

        bubble_height = 145

        draw_speech_bubble(
            canvas=canvas,
            text=panel.dialogue,
            x=(
                panel_width
                - bubble_width
                - 35
            ),
            y=110,
            width=bubble_width,
            height=bubble_height,
        )

    # --------------------------------------------------------
    # Bottom information area
    # --------------------------------------------------------

    info_top = (
        panel_height - 165
    )

    draw.rectangle(
        (
            0,
            info_top,
            panel_width,
            panel_height,
        ),
        fill="white",
        outline="black",
        width=4,
    )

    # --------------------------------------------------------
    # Caption
    # --------------------------------------------------------

    caption = (
        panel.caption
        or ""
    )

    if caption:

        draw_caption(
            canvas=canvas,
            text=caption,
            x=20,
            y=info_top + 15,
            width=310,
        )

    # --------------------------------------------------------
    # Narration
    # --------------------------------------------------------

    narration = (
        panel.narration
        or ""
    )

    narration_font = get_font(
        23,
        bold=False,
    )

    narration_lines = wrap_text(
        draw=draw,
        text=narration,
        font=narration_font,
        max_width=620,
    )

    narration_y = (
        info_top + 20
    )

    for line in narration_lines[:4]:

        draw.text(
            (
                350,
                narration_y,
            ),
            line,
            fill="black",
            font=narration_font,
        )

        narration_y += 30

    return canvas


# ============================================================
# BUILD COMPLETE COMIC
# ============================================================

def build_comic_layout(
    panels: List[ComicPanel],
) -> List[ComicPanel]:
    """
    Validate and prepare the five comic panels.

    The actual individual panel artwork is stored by the
    image generator. This function validates the structure
    and prepares the layout metadata.

    Returns exactly five ComicPanel objects.
    """

    if not panels:

        raise ValueError(
            "No panels were supplied."
        )

    if len(panels) != 5:

        raise ValueError(
            "ComicCraft requires exactly "
            "five panels."
        )

    for index, panel in enumerate(
        panels,
        start=1,
    ):

        panel.panel = index

        if not panel.title:

            panel.title = (
                f"Panel {index}"
            )

        if not panel.scene_description:

            panel.scene_description = (
                "A comic-book scene."
            )

        if not panel.narration:

            panel.narration = (
                panel.scene_description
            )

        if not panel.caption:

            panel.caption = (
                f"Panel {index}"
            )

    logger.info(
        "Comic layout validated: "
        "%s panels.",
        len(panels),
    )

    return panels


# ============================================================
# CREATE FULL COMIC IMAGE
# ============================================================

def render_full_comic(
    panels: List[ComicPanel],
    title: str = "ComicCraft",
) -> str:
    """
    Render all five panels into one large comic page.

    Layout:

        +---------------------------+
        |          TITLE            |
        +-------------+-------------+
        |   PANEL 1   |   PANEL 2   |
        +-------------+-------------+
        |   PANEL 3   |   PANEL 4   |
        +-------------+-------------+
        |         PANEL 5           |
        +---------------------------+
    """

    settings = get_settings()

    panels = build_comic_layout(
        panels
    )

    # --------------------------------------------------------
    # Dimensions
    # --------------------------------------------------------

    panel_width = 900
    panel_height = 760

    gap = 25

    title_height = 130

    page_width = (
        panel_width * 2
        + gap * 3
    )

    page_height = (
        title_height
        + panel_height * 3
        + gap * 4
    )

    # --------------------------------------------------------
    # Page
    # --------------------------------------------------------

    page = Image.new(
        "RGB",
        (
            page_width,
            page_height,
        ),
        "white",
    )

    draw = ImageDraw.Draw(
        page
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_font = get_font(
        58,
        bold=True,
    )

    title_text = (
        title
        or "ComicCraft"
    )

    bbox = draw.textbbox(
        (0, 0),
        title_text,
        font=title_font,
    )

    title_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (
                page_width
                - title_width
            ) // 2,
            35,
        ),
        title_text,
        fill="black",
        font=title_font,
    )

    # --------------------------------------------------------
    # Build panels
    # --------------------------------------------------------

    rendered_panels = []

    for panel in panels:

        rendered = build_panel(
            panel=panel,
            panel_width=panel_width,
            panel_height=panel_height,
        )

        rendered_panels.append(
            rendered
        )

    # --------------------------------------------------------
    # Panel positions
    # --------------------------------------------------------

    positions = [

        (
            gap,
            title_height + gap,
        ),

        (
            gap * 2
            + panel_width,
            title_height + gap,
        ),

        (
            gap,
            title_height
            + gap * 2
            + panel_height,
        ),

        (
            gap * 2
            + panel_width,
            title_height
            + gap * 2
            + panel_height,
        ),

        (
            (
                page_width
                - panel_width
            ) // 2,
            title_height
            + gap * 3
            + panel_height * 2,
        ),
    ]

    # --------------------------------------------------------
    # Paste panels
    # --------------------------------------------------------

    for image, position in zip(
        rendered_panels,
        positions,
    ):

        page.paste(
            image,
            position,
        )

    # --------------------------------------------------------
    # Outer page border
    # --------------------------------------------------------

    draw.rectangle(
        (
            5,
            5,
            page_width - 5,
            page_height - 5,
        ),
        outline="black",
        width=8,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    filename = (
        "comic_"
        f"{int(__import__('time').time() * 1000)}"
        ".png"
    )

    output_path = (
        settings.exports_dir
        / filename
    )

    page.save(
        output_path,
        format="PNG",
        optimize=True,
    )

    logger.info(
        "Full comic saved: %s",
        output_path,
    )

    return str(
        output_path
    )