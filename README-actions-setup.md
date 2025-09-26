# VTT Translator API — Deploy Notes

## Files
- `server.py` — FastAPI wrapper exposing `/translate-vtt`
- `vtt_multilang_translator.py` — the translator (already built)
- `requirements.txt` — OpenAI lib
- `requirements_api.txt` — FastAPI + Uvicorn
- `Dockerfile` — optional container deploy
- `openapi_actions.yaml` — paste into the Custom GPT "Actions" box after replacing the server URL

## Deploy (Render/Railway/Fly)
1) Create a new service from this folder.
2) Set env vars:
   - `OPENAI_API_KEY` = your OpenAI key
   - `API_BEARER` = a long random token (the Action will send this in Authorization header)
3) Start command (if needed): `uvicorn server:app --host 0.0.0.0 --port $PORT`
4) Note your public URL, e.g. `https://vtt-translator.onrender.com`

## Custom GPT — Actions
- In the GPT builder, go to **Actions → Add Action → Import from OpenAPI**.
- Paste the contents of `openapi_actions.yaml` with your **server URL** updated.
- Under **Authentication**, choose **API key** with Header name `Authorization` and Value `Bearer YOUR_TOKEN` (the same you set in `API_BEARER`).
- Save.

## Usage
In the GPT chat, upload a `.vtt` and say: "Translate to corporate languages." The GPT will call `/translate-vtt` and return a ZIP.