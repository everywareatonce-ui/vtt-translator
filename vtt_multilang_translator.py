#!/usr/bin/env python3
"""
vtt_multilang_translator.py

Translate a .vtt subtitle file into multiple target languages while preserving
timestamps, cue structure, speaker labels, and markup.

Usage:
  export OPENAI_API_KEY=sk-...
  python vtt_multilang_translator.py /path/to/file.vtt --langs ja-JP it-IT de-DE es-ES --model gpt-4o-mini
"""

import argparse, os, re, sys, json, time
from typing import List, Dict
from dataclasses import dataclass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

TIMECODE_RE = re.compile(
    r'^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*'
    r'(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})(?P<rest>.*)$'
)

@dataclass
class Cue:
    idx: int
    timecode: str
    text_lines: List[str]

def parse_vtt(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or not lines[0].startswith("WEBVTT"):
        raise ValueError("Not a VTT file")

    # Skip header lines
    i = 1
    while i < len(lines) and lines[i].strip() != "":
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        i += 1

    cues = []
    idx = 0
    while i < len(lines):
        if lines[i].strip().isdigit():
            i += 1
        if i >= len(lines):
            break
        if not TIMECODE_RE.match(lines[i]):
            i += 1
            continue
        timecode = lines[i]; i += 1
        text = []
        while i < len(lines) and lines[i].strip() != "":
            text.append(lines[i]); i += 1
        if i < len(lines) and lines[i].strip() == "":
            i += 1
        cues.append(Cue(idx, timecode, text))
        idx += 1
    return "WEBVTT", cues

SYSTEM_PROMPT = """You are a professional subtitle translator.
Translate only the natural language text into the TARGET language.
Preserve:
- timestamps (not for translation)
- cue order and count
- line breaks inside cues
- speaker labels (>> or NAME:)
- inline tags (<i>, <b>, <u>, <c>, <v>, <lang>)
- numbers, product codes, acronyms
Return JSON with: {"items": [{"id":0,"text":"..."}, ...]}.
"""

def translate_batch(client, model, batch: List[Cue], lang: str):
    payload = [{"id": c.idx, "text": "\n".join(c.text_lines)} for c in batch]
    user_prompt = json.dumps({"TARGET": lang, "items": payload}, ensure_ascii=False)
    resp = client.responses.create(
        model=model,
        temperature=0,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    data = json.loads(resp.output_text)
    return {int(item["id"]): item["text"] for item in data["items"]}

def write_vtt(header: str, cues: List[Cue], translations: Dict[int, str], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n\n")
        for c in cues:
            f.write(f"{c.idx+1}\n")
            f.write(c.timecode + "\n")
            t = translations.get(c.idx, "\n".join(c.text_lines))
            f.write(t + "\n\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vtt", help="Path to input .vtt")
    ap.add_argument("--langs", nargs="+", required=True, help="Target languages, e.g. ja-JP de-DE")
    ap.add_argument("--model", default="gpt-4o-mini", help="Model to use")
    args = ap.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    header, cues = parse_vtt(args.vtt)

    for lang in args.langs:
        translations = {}
        for i in range(0, len(cues), 50):
            sub = cues[i:i+50]
            translations.update(translate_batch(client, args.model, sub, lang))
        out_path = os.path.splitext(args.vtt)[0] + "." + lang + ".vtt"
        write_vtt(header, cues, translations, out_path)
        print("Wrote", out_path)

if __name__ == "__main__":
    main()