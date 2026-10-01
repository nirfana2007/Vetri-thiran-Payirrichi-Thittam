import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from huggingface_hub import InferenceClient

app = FastAPI(title="Comic Craft")


class ComicRequest(BaseModel):
    title: str
    prompt: str


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/submit")
def submit_comic(data: ComicRequest):
    return {
        "message": "Submission successful!",
        "title": data.title,
        "prompt": data.prompt
    }


@app.post("/generate")
def generate_comic(data: ComicRequest):

    token = os.environ.get("HF_TOKEN")

    if not token:
        return {
            "error": "HF_TOKEN is not set"
        }

    try:
        client = InferenceClient(
            api_key=token
        )

        image = client.text_to_image(
            prompt=f"""
            Create a high quality colorful comic illustration.

            Title: {data.title}

            Story:
            {data.prompt}

            Comic book style,
            expressive characters,
            detailed background,
            cinematic lighting,
            vibrant colors.
            """,
            model="black-forest-labs/FLUX.1-schnell"
        )

        output_path = "static/generated_comic.png"
        image.save(output_path)

        return {
            "message": "Image generated successfully!",
            "image": "/generated_comic.png"
        }

    except Exception as e:
        return {
            "error": str(e)
        }