import os
import tempfile
import subprocess
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import zipfile

# Security: simple bearer token so only your GPT Action can call this
API_BEARER = os.getenv("API_BEARER", "")

def verify_bearer(auth_header: Optional[str]):
    if not API_BEARER:
        return  # no auth enforced if empty
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != API_BEARER:
        raise HTTPException(status_code=403, detail="Invalid token")

app = FastAPI(title="VTT Translator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default set of corporate languages
DEFAULT_LANGS = [
    "sv-SE","nb-NO","da-DK","de-DE","fr-FR",
    "it-IT","es-ES","nl-NL","zh-Hans","zh-Hant",
    "ja-JP","ko-KR"
]

@app.post("/translate-vtt")
async def translate_vtt(
    file: UploadFile = File(..., description="Source .vtt file"),
    wrap: int = Form(42),
    model: str = Form("gpt-4o-mini"),
    langs: Optional[str] = Form(None, description="Space-separated language codes; defaults to corporate 12"),
    authorization: Optional[str] = Header(None)
):
    verify_bearer(authorization)

    if not file.filename.lower().endswith(".vtt"):
        raise HTTPException(status_code=400, detail="Only .vtt files are supported")

    # Build language list
    langs_list: List[str] = DEFAULT_LANGS if not langs else langs.split()

    # Ensure translator script is present
    translator_path = os.path.join(os.path.dirname(__file__), "vtt_multilang_translator.py")
    if not os.path.exists(translator_path):
        raise HTTPException(status_code=500, detail="Translator script not found on server")

    # Check OpenAI key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set on server")

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, file.filename)
        with open(src_path, "wb") as f:
            f.write(await file.read())

        # Run translator script
        cmd = [
            "python", translator_path,
            src_path,
            "--langs", *langs_list,
            "--model", model,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                status_code=500,
                content={"error": "translation_failed", "stdout": e.stdout, "stderr": e.stderr},
            )

        # Zip outputs
        zip_path = os.path.join(tmp, "translations.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            base = os.path.splitext(os.path.basename(src_path))[0]
            for name in os.listdir(tmp):
                if name.startswith(base + ".") and name.endswith(".vtt"):
                    z.write(os.path.join(tmp, name), arcname=name)

        return FileResponse(zip_path, media_type="application/zip", filename="translations.zip")


# ------------------------
# Extra endpoints
# ------------------------

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
      <h2>VTT Translator API</h2>
      <p>Use <code>/translate-vtt</code> to upload .vtt files.</p>
      <p>See <a href="/privacy">Privacy Policy</a> and <a href="/terms">Terms of Use</a>.</p>
    </body></html>
    """

@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return """
    <html><head><title>Privacy Policy — VTT Translator</title></head>
    <body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
      <h1>Privacy Policy — VTT Translator</h1>
      <p><strong>Last updated:</strong> 2025-09-26</p>
      <p>When you use the action, you upload a WebVTT (.vtt) file. The service processes
         only the text content to produce translations. Uploaded files and generated
         outputs are stored temporarily during processing and then deleted. We do not
         log or persist subtitle text.</p>
      <p>Data is sent to OpenAI's API for translation. We do not sell or share your data.</p>
      <p>Access is restricted via a bearer token.</p>
      <p>For questions, contact: <a href="mailto:owner@example.com">owner@example.com</a></p>
    </body></html>
    """

@app.get("/terms", response_class=HTMLResponse)
def terms():
    return """
    <html><head><title>Terms of Use — VTT Translator</title></head>
    <body style="font-family: sans-serif; max-width: 720px; margin: 2rem auto;">
      <h1>Terms of Use — VTT Translator</h1>
      <p><strong>Last updated:</strong> 2025-09-26</p>
      <ul>
        <li>You must have the right to process the content you upload.</li>
        <li>No illegal, abusive, or infringing content.</li>
        <li>No attempts to bypass authentication or probe the service.</li>
      </ul>
      <p>The service is provided “as is” without warranties. Output may contain errors. 
         You are responsible for verifying translations.</p>
      <p>We disclaim liability to the maximum extent permitted by law.</p>
    </body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok"}
