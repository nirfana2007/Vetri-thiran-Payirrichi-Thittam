import logging
from pathlib import Path
from typing import List, Optional

from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.layout_builder import build_panel
from app.models import ComicPanel


logger = logging.getLogger(__name__)


# ============================================================
# PDF PAGE SETTINGS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

PAGE_MARGIN = 30


# ============================================================
# FIND IMAGE
# ============================================================

def find_panel_image(
    panel: ComicPanel,
) -> Optional[Path]:
    """
    Find the generated image belonging to a comic panel.
    """

    if not panel.image_path:
        return None

    path = Path(
        panel.image_path
    )

    if path.exists():
        return path

    return None


# ============================================================
# DRAW IMAGE TO PDF
# ============================================================

def draw_image_on_pdf(
    pdf: canvas.Canvas,
    image_path: Path,
    x: float,
    y: float,
    width: float,
    height: float,
):
    """
    Draw an image inside a PDF while preserving
    its aspect ratio.
    """

    try:

        with Image.open(
            image_path
        ) as image:

            image_width, image_height = (
                image.size
            )

        if (
            image_width <= 0
            or image_height <= 0
        ):
            return

        image_ratio = (
            image_width
            / image_height
        )

        box_ratio = (
            width
            / height
        )

        if image_ratio > box_ratio:

            # Image is wider than the PDF box.

            draw_width = width

            draw_height = (
                width
                / image_ratio
            )

        else:

            # Image is taller than the PDF box.

            draw_height = height

            draw_width = (
                height
                * image_ratio
            )

        draw_x = (
            x
            + (width - draw_width)
            / 2
        )

        draw_y = (
            y
            + (height - draw_height)
            / 2
        )

        pdf.drawImage(
            ImageReader(
                str(image_path)
            ),
            draw_x,
            draw_y,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )

    except Exception as exc:

        logger.warning(
            "Could not draw image %s: %s",
            image_path,
            exc,
        )


# ============================================================
# DRAW TEXT
# ============================================================

def draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str = "Helvetica",
    font_size: float = 10,
    line_height: float = 13,
):
    """
    Draw wrapped text inside a PDF.
    """

    if not text:
        return y

    pdf.setFont(
        font_name,
        font_size,
    )

    words = text.split()

    lines = []

    current_line = ""

    for word in words:

        candidate = (
            f"{current_line} {word}".strip()
        )

        if (
            pdf.stringWidth(
                candidate,
                font_name,
                font_size,
            )
            <= max_width
        ):

            current_line = candidate

        else:

            if current_line:
                lines.append(
                    current_line
                )

            current_line = word

    if current_line:
        lines.append(
            current_line
        )

    for line in lines:

        pdf.drawString(
            x,
            y,
            line,
        )

        y -= line_height

    return y


# ============================================================
# DRAW PDF HEADER
# ============================================================

def draw_pdf_header(
    pdf: canvas.Canvas,
    title: str,
    page_number: int,
):
    """
    Draw the title and page number.
    """

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )

    pdf.drawString(
        PAGE_MARGIN,
        PAGE_HEIGHT - PAGE_MARGIN,
        title,
    )

    pdf.setFont(
        "Helvetica",
        9,
    )

    page_text = (
        f"Page {page_number}"
    )

    page_width = pdf.stringWidth(
        page_text,
        "Helvetica",
        9,
    )

    pdf.drawString(
        PAGE_WIDTH
        - PAGE_MARGIN
        - page_width,
        PAGE_HEIGHT - PAGE_MARGIN,
        page_text,
    )


# ============================================================
# DRAW PANEL
# ============================================================

def draw_panel_to_pdf(
    pdf: canvas.Canvas,
    panel: ComicPanel,
    panel_number: int,
    x: float,
    y: float,
    width: float,
    height: float,
):
    """
    Draw one complete comic panel into the PDF.

    Includes:

    - artwork
    - border
    - panel number
    - title
    - narration
    - dialogue
    """

    # --------------------------------------------------------
    # Panel border
    # --------------------------------------------------------

    pdf.setLineWidth(2)

    pdf.rect(
        x,
        y,
        width,
        height,
        stroke=1,
        fill=0,
    )

    # --------------------------------------------------------
    # Artwork
    # --------------------------------------------------------

    image_path = (
        find_panel_image(panel)
    )

    artwork_height = (
        height * 0.68
    )

    if image_path:

        draw_image_on_pdf(
            pdf=pdf,
            image_path=image_path,
            x=x + 4,
            y=(
                y
                + height
                - artwork_height
                + 4
            ),
            width=width - 8,
            height=artwork_height - 8,
        )

    else:

        pdf.setFont(
            "Helvetica-Bold",
            14,
        )

        text = (
            "Image unavailable"
        )

        text_width = pdf.stringWidth(
            text,
            "Helvetica-Bold",
            14,
        )

        pdf.drawString(
            x
            + (
                width
                - text_width
            )
            / 2,
            y
            + height
            - artwork_height / 2,
            text,
        )

    # --------------------------------------------------------
    # Panel number
    # --------------------------------------------------------

    number_box_size = 25

    pdf.setFillColorRGB(
        1,
        1,
        1,
    )

    pdf.rect(
        x + 8,
        y + height - 33,
        number_box_size,
        number_box_size,
        stroke=1,
        fill=1,
    )

    pdf.setFillColorRGB(
        0,
        0,
        0,
    )

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawCentredString(
        x + 8 + number_box_size / 2,
        y + height - 25,
        str(panel_number),
    )

    # --------------------------------------------------------
    # Text area
    # --------------------------------------------------------

    text_x = x + 12

    text_width = (
        width - 24
    )

    text_y = (
        y
        + height
        - artwork_height
        - 18
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if panel.title:

        pdf.setFont(
            "Helvetica-Bold",
            12,
        )

        text_y = draw_wrapped_text(
            pdf=pdf,
            text=panel.title,
            x=text_x,
            y=text_y,
            max_width=text_width,
            font_name="Helvetica-Bold",
            font_size=12,
            line_height=14,
        )

        text_y -= 5

    # --------------------------------------------------------
    # Narration
    # --------------------------------------------------------

    if panel.narration:

        pdf.setFont(
            "Helvetica",
            9,
        )

        text_y = draw_wrapped_text(
            pdf=pdf,
            text=panel.narration,
            x=text_x,
            y=text_y,
            max_width=text_width,
            font_name="Helvetica",
            font_size=9,
            line_height=12,
        )

        text_y -= 5

    # --------------------------------------------------------
    # Dialogue
    # --------------------------------------------------------

    if panel.dialogue:

        pdf.setFont(
            "Helvetica-Oblique",
            9,
        )

        dialogue_text = (
            f'"{panel.dialogue}"'
        )

        draw_wrapped_text(
            pdf=pdf,
            text=dialogue_text,
            x=text_x,
            y=text_y,
            max_width=text_width,
            font_name="Helvetica-Oblique",
            font_size=9,
            line_height=12,
        )


# ============================================================
# SAVE PDF
# ============================================================

def save_pdf(
    layout: List[ComicPanel],
    title: str = "ComicCraft Comic",
    character_name: str = "",
    setting: str = "",
    tone: str = "",
    art_style: str = "",
) -> str:
    """
    Export the completed five-panel comic as a PDF.

    The PDF contains:

    Page 1:
        Comic title
        Character
        Setting
        Tone
        Art style

    Page 2:
        Panels 1 and 2

    Page 3:
        Panels 3 and 4

    Page 4:
        Panel 5
    """

    settings = get_settings()

    # --------------------------------------------------------
    # Validate panels
    # --------------------------------------------------------

    if not layout:

        raise ValueError(
            "Cannot export an empty comic."
        )

    if len(layout) != 5:

        raise ValueError(
            "ComicCraft PDF export requires "
            "exactly five panels."
        )

    # --------------------------------------------------------
    # Create exports directory
    # --------------------------------------------------------

    settings.exports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Generate filename
    # --------------------------------------------------------

    import time

    timestamp = int(
        time.time()
    )

    safe_name = (
        "".join(
            character_name
            .strip()
            .split()
        )
        if character_name
        else "comic"
    )

    filename = (
        f"{safe_name}_comic_"
        f"{timestamp}.pdf"
    )

    output_path = (
        settings.exports_dir
        / filename
    )

    # --------------------------------------------------------
    # Create PDF
    # --------------------------------------------------------

    pdf = canvas.Canvas(
        str(output_path),
        pagesize=A4,
    )

    pdf.setTitle(
        title
    )

    pdf.setAuthor(
        "ComicCraft"
    )

    # ========================================================
    # PAGE 1 — COVER
    # ========================================================

    pdf.setFont(
        "Helvetica-Bold",
        30,
    )

    title_width = pdf.stringWidth(
        title,
        "Helvetica-Bold",
        30,
    )

    pdf.drawString(
        (
            PAGE_WIDTH
            - title_width
        ) / 2,
        PAGE_HEIGHT - 150,
        title,
    )

    # --------------------------------------------------------
    # Subtitle
    # --------------------------------------------------------

    pdf.setFont(
        "Helvetica",
        14,
    )

    subtitle = (
        "Created with ComicCraft"
    )

    subtitle_width = (
        pdf.stringWidth(
            subtitle,
            "Helvetica",
            14,
        )
    )

    pdf.drawString(
        (
            PAGE_WIDTH
            - subtitle_width
        ) / 2,
        PAGE_HEIGHT - 180,
        subtitle,
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata_y = (
        PAGE_HEIGHT - 270
    )

    metadata = [
        (
            "Character",
            character_name,
        ),
        (
            "Setting",
            setting,
        ),
        (
            "Tone",
            tone,
        ),
        (
            "Art Style",
            art_style,
        ),
        (
            "Panels",
            "5",
        ),
    ]

    for label, value in metadata:

        pdf.setFont(
            "Helvetica-Bold",
            12,
        )

        pdf.drawString(
            PAGE_MARGIN + 80,
            metadata_y,
            f"{label}:",
        )

        pdf.setFont(
            "Helvetica",
            12,
        )

        pdf.drawString(
            PAGE_MARGIN + 170,
            metadata_y,
            value or "N/A",
        )

        metadata_y -= 32

    # --------------------------------------------------------
    # Cover description
    # --------------------------------------------------------

    pdf.setFont(
        "Helvetica",
        11,
    )

    cover_description = (
        "A five-panel AI-generated comic "
        "story created from your idea."
    )

    draw_wrapped_text(
        pdf=pdf,
        text=cover_description,
        x=PAGE_MARGIN + 80,
        y=metadata_y - 30,
        max_width=PAGE_WIDTH - 160,
        font_name="Helvetica",
        font_size=11,
        line_height=16,
    )

    pdf.showPage()

    # ========================================================
    # PAGE 2 — PANELS 1 & 2
    # ========================================================

    draw_pdf_header(
        pdf,
        title,
        page_number=2,
    )

    panel_width = (
        PAGE_WIDTH
        - PAGE_MARGIN * 2
        - 15
    ) / 2

    panel_height = (
        PAGE_HEIGHT
        - PAGE_MARGIN * 2
        - 70
    )

    panel_y = (
        PAGE_MARGIN
        + 20
    )

    draw_panel_to_pdf(
        pdf=pdf,
        panel=layout[0],
        panel_number=1,
        x=PAGE_MARGIN,
        y=panel_y,
        width=panel_width,
        height=panel_height,
    )

    draw_panel_to_pdf(
        pdf=pdf,
        panel=layout[1],
        panel_number=2,
        x=(
            PAGE_MARGIN
            + panel_width
            + 15
        ),
        y=panel_y,
        width=panel_width,
        height=panel_height,
    )

    pdf.showPage()

    # ========================================================
    # PAGE 3 — PANELS 3 & 4
    # ========================================================

    draw_pdf_header(
        pdf,
        title,
        page_number=3,
    )

    draw_panel_to_pdf(
        pdf=pdf,
        panel=layout[2],
        panel_number=3,
        x=PAGE_MARGIN,
        y=panel_y,
        width=panel_width,
        height=panel_height,
    )

    draw_panel_to_pdf(
        pdf=pdf,
        panel=layout[3],
        panel_number=4,
        x=(
            PAGE_MARGIN
            + panel_width
            + 15
        ),
        y=panel_y,
        width=panel_width,
        height=panel_height,
    )

    pdf.showPage()

    # ========================================================
    # PAGE 4 — PANEL 5
    # ========================================================

    draw_pdf_header(
        pdf,
        title,
        page_number=4,
    )

    final_width = (
        PAGE_WIDTH
        - PAGE_MARGIN * 2
    )

    final_height = (
        PAGE_HEIGHT
        - PAGE_MARGIN * 2
        - 70
    )

    draw_panel_to_pdf(
        pdf=pdf,
        panel=layout[4],
        panel_number=5,
        x=PAGE_MARGIN,
        y=PAGE_MARGIN + 20,
        width=final_width,
        height=final_height,
    )

    pdf.showPage()

    # --------------------------------------------------------
    # Finish PDF
    # --------------------------------------------------------

    pdf.save()

    logger.info(
        "PDF successfully exported: %s",
        output_path,
    )

    return str(
        output_path
    )