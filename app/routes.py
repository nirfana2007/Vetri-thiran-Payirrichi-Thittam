import logging
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
)
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.gemini_flash import generate_outline
from app.gemini_pro import generate_script
from app.image_generator import generate_image
from app.layout_builder import build_comic_layout
from app.exporters import save_pdf
from app.models import ComicRequest


logger = logging.getLogger(__name__)

router = APIRouter()

settings = get_settings()

templates = Jinja2Templates(
    directory=str(
        settings.templates_dir
    )
)


# ============================================================
# Helper: Generate the complete comic
# ============================================================

def generate_complete_comic(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
):
    """
    Runs the complete ComicCraft pipeline:

    1. Gemini Flash
       -> five-panel outline

    2. Gemini Pro
       -> narration, dialogue and captions

    3. Image generator
       -> one image per panel

    4. Layout builder
       -> complete five-panel comic

    5. PDF exporter
       -> downloadable PDF
    """

    logger.info(
        "Starting comic generation for character=%s",
        character_name,
    )

    # --------------------------------------------------------
    # Step 1: Generate five-panel outline
    # --------------------------------------------------------

    outline = generate_outline(
        story_prompt=story_prompt,
        character_name=character_name,
        setting=setting,
        tone=tone,
        art_style=art_style,
    )

    if not outline:
        raise RuntimeError(
            "Story outline generation failed."
        )

    if len(outline) != 5:
        raise RuntimeError(
            "Comic outline must contain exactly "
            "five panels."
        )

    logger.info(
        "Five-panel outline generated."
    )

    # --------------------------------------------------------
    # Step 2: Expand outline into comic script
    # --------------------------------------------------------

    panels = generate_script(
        outline=outline,
        character_name=character_name,
        setting=setting,
        tone=tone,
        art_style=art_style,
    )

    if not panels:
        raise RuntimeError(
            "Comic script generation failed."
        )

    if len(panels) != 5:
        raise RuntimeError(
            "Comic script must contain exactly "
            "five panels."
        )

    logger.info(
        "Comic script generated."
    )

    # --------------------------------------------------------
    # Step 3: Generate panel images
    # --------------------------------------------------------

    for index, panel in enumerate(
        panels,
        start=1,
    ):

        logger.info(
            "Generating image for panel %s",
            index,
        )

        image_path = generate_image(
            prompt=panel.image_prompt,
            panel_number=index,
            art_style=art_style,
        )

        if not image_path:
            raise RuntimeError(
                f"Image generation failed "
                f"for panel {index}."
            )

        panel.image_path = image_path

    logger.info(
        "All five panel images generated."
    )

    # --------------------------------------------------------
    # Step 4: Build final comic layout
    # --------------------------------------------------------

    layout = build_comic_layout(
        panels=panels,
    )

    if len(layout) != 5:
        raise RuntimeError(
            "Comic layout must contain exactly "
            "five panels."
        )

    # --------------------------------------------------------
    # Step 5: Create PDF
    # --------------------------------------------------------

    comic_title = (
        f"{character_name}'s "
        f"Adventure in {setting}"
    )

    pdf_path = save_pdf(
        layout=layout,
        title=comic_title,
        character_name=character_name,
        setting=setting,
        tone=tone,
        art_style=art_style,
    )

    logger.info(
        "Comic PDF generated: %s",
        pdf_path,
    )

    return {
        "comic_title": comic_title,
        "character_name": character_name,
        "setting": setting,
        "tone": tone,
        "art_style": art_style,
        "panels": layout,
        "pdf_path": pdf_path,
    }


# ============================================================
# Home page
# ============================================================

@router.get(
    "/",
    response_class=HTMLResponse,
)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "error_message": None,
        },
    )


# ============================================================
# HTML comic generation
# ============================================================

@router.post(
    "/generate",
    response_class=HTMLResponse,
)
async def generate_comic(
    request: Request,

    story_prompt: str = Form(...),

    character_name: str = Form(...),

    setting: str = Form(...),

    custom_setting: Optional[str] = Form(
        None
    ),

    tone: str = Form(...),

    art_style: str = Form(...),
):

    try:

        story_prompt = story_prompt.strip()

        character_name = (
            character_name.strip()
        )

        setting = setting.strip()

        tone = tone.strip()

        art_style = art_style.strip()

        # ----------------------------------------------------
        # Validate basic input
        # ----------------------------------------------------

        if len(story_prompt) < 3:
            raise ValueError(
                "Story prompt is too short."
            )

        if len(character_name) < 1:
            raise ValueError(
                "Character name is required."
            )

        # ----------------------------------------------------
        # Custom setting
        # ----------------------------------------------------

        if setting.lower() == "custom":

            if not custom_setting:
                raise ValueError(
                    "Please enter a custom setting."
                )

            setting = (
                custom_setting.strip()
            )

            if not setting:
                raise ValueError(
                    "Custom setting cannot be empty."
                )

        # ----------------------------------------------------
        # Generate complete comic
        # ----------------------------------------------------

        result = generate_complete_comic(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style,
        )

        # ----------------------------------------------------
        # Render Comic Preview
        # ----------------------------------------------------

        return templates.TemplateResponse(
            request=request,
            name="comic_preview.html",
            context=result,
        )

    except Exception as exc:

        logger.exception(
            "Comic generation failed."
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error_message": str(exc),
            },
            status_code=500,
        )


# ============================================================
# JSON API
# ============================================================

@router.post(
    "/api/generate",
)
async def generate_comic_api(
    payload: ComicRequest,
):

    try:

        setting = payload.setting.strip()

        result = generate_complete_comic(
            story_prompt=payload.story_prompt.strip(),
            character_name=payload.character_name.strip(),
            setting=setting,
            tone=payload.tone.strip(),
            art_style=payload.art_style.strip(),
        )

        return {
            "success": True,
            **result,
        }

    except Exception as exc:

        logger.exception(
            "JSON comic generation failed."
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# ============================================================
# Image test endpoint
# ============================================================

@router.get(
    "/test-image",
)
async def test_image(
    prompt: str = Query(
        default=(
            "A brave young fox "
            "exploring an enchanted forest"
        ),
        min_length=1,
        max_length=2000,
    ),

    panel: int = Query(
        default=1,
        ge=1,
        le=5,
    ),

    art_style: str = Query(
        default="Comic Book",
        min_length=1,
        max_length=100,
    ),
):

    try:

        image_path = generate_image(
            prompt=prompt,
            panel_number=panel,
            art_style=art_style,
        )

        return {
            "success": True,
            "image_path": image_path,
        }

    except Exception as exc:

        logger.exception(
            "Test image generation failed."
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# ============================================================
# PDF download
# ============================================================

@router.get(
    "/download-pdf",
)
async def download_pdf(
    file: str = Query(
        ...,
        min_length=1,
    ),
):

    exports_dir = (
        settings.exports_dir.resolve()
    )

    # --------------------------------------------------------
    # Convert requested path
    # --------------------------------------------------------

    requested_path = (
        settings.static_dir.parent
        / file.lstrip("/")
    ).resolve()

    # --------------------------------------------------------
    # Security:
    # Make sure the requested file is actually inside
    # static/exports.
    # --------------------------------------------------------

    try:

        requested_path.relative_to(
            exports_dir
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid PDF path.",
        )

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    if (
        requested_path.suffix.lower()
        != ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files can be downloaded.",
        )

    # --------------------------------------------------------
    # Check file exists
    # --------------------------------------------------------

    if not requested_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="PDF file not found.",
        )

    # --------------------------------------------------------
    # Send PDF
    # --------------------------------------------------------

    return FileResponse(
        path=str(requested_path),
        media_type="application/pdf",
        filename=requested_path.name,
    )


# ============================================================
# Health check
# ============================================================

@router.get(
    "/api/health",
)
async def api_health():

    return {
        "success": True,
        "status": "healthy",
        "service": "ComicCraft",
    }