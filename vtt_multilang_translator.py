"""
VTT Multilang Translator
Translates WebVTT (.vtt) subtitle files into multiple target languages.

Usage:
    export OPENAI_API_KEY=sk-...
    python vtt_multilang_translator.py /path/to/file.vtt --langs ja-JP it-IT de-DE es-ES --wrap 42
"""

import argparse, os, re, sys, json, time
from typing import List, Dict
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DEFAULT_LANGS = [
    "de-DE", "fr-FR", "it-IT", "nl-NL",
    "da-DK", "es-ES", "nb-NO", "sv-SE",
    "zh-CN", "zh-TW", "ja-JP", "ko-KR"
]

def parse_vtt(text: str) -> List[Dict]:
    """Parse .vtt file into list of cues."""
    blocks = re.split(r"\n\n+", text.strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        cue = {"id": None, "time": None, "text": []}
        if re.match(r"^\d+$", lines[0]):
            cue["id"] = lines[0]
            lines = lines[1:]
        if lines and "-->" in lines[0]:
            cue["time"] = lines[0]
            lines = lines[1:]
        cue["text"] = lines
        cues.append(cue)
    return cues

def reassemble_vtt(cues: List[Dict]) -> str:
    """Reassemble cues into VTT text."""
    out = ["WEBVTT\n"]
    for cue in cues:
        if cue["id"]:
            out.append(cue["id"])
        if cue["time"]:
            out.append(cue["time"])
        out.extend(cue["text"])
        out.append("")  # blank line
    return "\n".join(out).strip() + "\n"

def translate_text(text: str, target_lang: str, model: str = "gpt-4.1-mini", wrap: int = 42) -> str:
    """Translate a block of text into the target language."""
    prompt = f"""You are a subtitle translator.
Translate the following lines into {target_lang}.
Rules:
- Keep cue numbers, timestamps, and settings unchanged.
- Only translate the spoken text.
- Keep line breaks and brackets (like [music]) intact.
- Wrap lines at ~{wrap} characters max.

Text:
{text}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

def translate_vtt_file(infile: str, langs: List[str], model: str = "gpt-4.1-mini", wrap: int = 42):
    """Translate a .vtt file into multiple target languages."""
    with open(infile, "r", encoding="utf-8") as f:
        src_text = f.read()

    cues = parse_vtt(src_text)

    results = {}
    for lang in langs:
        translated_cues = []
        for cue in cues:
            if not cue["text"]:
                translated_cues.append(cue.copy())
                continue
            joined = "\n".join(cue["text"])
            translated = translate_text(joined, lang, model=model, wrap=wrap)
            new_cue = cue.copy()
            new_cue["text"] = translated.splitlines()
            translated_cues.append(new_cue)
        results[lang] = reassemble_vtt(translated_cues)

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="Input .vtt file")
    parser.add_argument("--langs", nargs="+", default=DEFAULT_LANGS, help="Target language codes")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model (default gpt-4.1-mini)")
    parser.add_argument("--wrap", type=int, default=42, help="Line wrap length")
    args = parser.parse_args()

    outputs = translate_vtt_file(args.infile, args.langs, model=args.model, wrap=args.wrap)

    base = os.path.splitext(args.infile)[0]
    for lang, text in outputs.items():
        outname = f"{base}.{lang}.vtt"
        with open(outname, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {outname}")

if __name__ == "__main__":
    main()
