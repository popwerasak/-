#!/usr/bin/env python3
"""Transcribe the speech in a video into timed segments (any language).

Usage: transcribe.py VIDEO -o segments.json [--model small] [--language en]

Output: {"language": "en", "duration": 42.1,
         "segments": [{"start": 0.0, "end": 3.4, "text": "..."}]}

Needs: ffmpeg and `pip install faster-whisper` (the model downloads from
huggingface.co on first use).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--model", default="small", help="tiny | base | small | medium | large-v3")
    ap.add_argument("--language", help="source language code; auto-detected if omitted")
    a = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is missing. Run: pip install faster-whisper")

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-vn",
                            "-ar", "16000", "-ac", "1", wav], capture_output=True, text=True)
        if p.returncode != 0 or not os.path.exists(wav):
            sys.exit("Could not extract audio - the video may have no sound track.\n" + p.stderr[-500:])
        try:
            model = WhisperModel(a.model, device="cpu", compute_type="int8")
        except Exception as e:
            sys.exit(f"Could not load the speech model ({e}).\n"
                     "The machine needs access to huggingface.co to download it.")
        segments, info = model.transcribe(wav, language=a.language, vad_filter=True)
        out = {"language": info.language, "duration": round(info.duration, 2),
               "segments": [{"start": round(s.start, 2), "end": round(s.end, 2),
                             "text": s.text.strip()} for s in segments if s.text.strip()]}

    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {a.output}: {len(out['segments'])} segments, language={out['language']}")


if __name__ == "__main__":
    main()
