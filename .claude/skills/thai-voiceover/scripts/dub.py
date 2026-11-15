#!/usr/bin/env python3
"""Add a natural Thai voice-over (male / female neural voices) to a video.

Usage:
  dub.py VIDEO SCRIPT -o OUT.mp4 [--voice female] [--original low|duck|mute|keep]
  dub.py --sample "ข้อความทดสอบ" --voice male -o sample.mp3
  dub.py --list-voices

SCRIPT is one of:
  .json  {"voice": "female", "segments": [{"start": 0.0, "end": 3.5,
          "text": "...", "voice": "male"}]}   (timed; per-segment voice optional)
  .srt   timed subtitles (spoken as-is)
  .txt   plain narration, one sentence/phrase per line (laid out back to back)

Only needs: python3, ffmpeg/ffprobe, `pip install edge-tts`.
"""
import argparse
import array
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))


def load_voices():
    with open(os.path.join(HERE, "voices.json"), encoding="utf-8") as f:
        return json.load(f)


def resolve_voice(name, voices):
    """Return (edge voice id, rate %, pitch Hz) for a preset name or alias."""
    key = (name or "female").strip().lower()
    for preset, v in voices.items():
        if key == preset or key in [a.lower() for a in v.get("aliases", [])]:
            return v["voice"], v.get("rate", 0), v.get("pitch", 0)
    if key.startswith("th-th-"):  # a raw edge-tts voice id
        return name, 0, 0
    sys.exit(f"Unknown voice '{name}'. Choose from: {', '.join(voices)}")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p.stdout


def probe(video):
    out = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type", "-of", "json", video]))
    has_audio = any(s["codec_type"] == "audio" for s in out["streams"])
    return float(out["format"]["duration"]), has_audio


# ---------- script parsing ----------

def parse_time(t):
    h, m, s = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(text):
    segs = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        for i, l in enumerate(lines):
            m = re.match(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", l)
            if m:
                body = " ".join(lines[i + 1:]).strip()
                if body:
                    segs.append({"start": parse_time(m.group(1)),
                                 "end": parse_time(m.group(2)), "text": body})
                break
    return segs


def load_script(path):
    """Return (default_voice or None, segments, timed?)."""
    raw = open(path, encoding="utf-8-sig").read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        data = json.loads(raw)
        if isinstance(data, list):
            data = {"segments": data}
        segs = [s for s in data["segments"] if s.get("text", "").strip()]
        timed = all("start" in s for s in segs)
        return data.get("voice"), segs, timed
    if ext == ".srt":
        return None, parse_srt(raw), True
    segs = [{"text": l.strip()} for l in raw.splitlines() if l.strip()]
    return None, segs, False


# ---------- speech synthesis ----------

def _edge():
    try:
        import edge_tts
        import edge_tts.communicate as comm
    except ImportError:
        sys.exit("edge-tts is missing. Run: pip install edge-tts")
    # Honour a custom CA bundle (corporate / sandbox proxies) instead of failing TLS.
    ca = os.environ.get("SSL_CERT_FILE")
    if ca and os.path.exists(ca) and not getattr(comm, "_ca_loaded", False):
        try:
            comm._SSL_CTX.load_verify_locations(ca)
            comm._ca_loaded = True
        except Exception:
            pass
    return edge_tts


class SpeechError(Exception):
    pass


CACHE = os.path.join(os.path.expanduser("~"), ".cache", "thai-voiceover")


async def tts(text, voice, rate, pitch, out_mp3):
    """Speak one line to out_mp3. Finished lines are cached, so a re-run after a
    failure (or after editing a few lines of the script) only requests what is new."""
    rate, pitch = round(rate), round(pitch)
    key = hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode()).hexdigest()
    cached = os.path.join(CACHE, key + ".mp3")
    if os.path.exists(cached) and os.path.getsize(cached) > 0:
        shutil.copyfile(cached, out_mp3)
        return
    edge_tts = _edge()
    last = None
    # The free endpoint sometimes answers "No audio was received" for one particular
    # line and keeps doing so for 1-2 minutes before the same request works again,
    # so the retries are spread over about three minutes rather than fired quickly.
    delays = (3, 5, 8, 12, 15, 20, 25, 30, 30, 30)
    for attempt, delay in enumerate(delays):
        try:
            c = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz")
            await c.save(out_mp3)
            if os.path.getsize(out_mp3) > 0:
                os.makedirs(CACHE, exist_ok=True)
                shutil.copyfile(out_mp3, cached)
                return
        except Exception as e:
            last = e
        if attempt == 1:
            print(f"  speech service is slow for \"{text[:30]}...\" - retrying for up to 3 min",
                  flush=True)
        await asyncio.sleep(delay)
    if os.path.exists(out_mp3):
        os.remove(out_mp3)
    raise SpeechError(f"{text[:50]} ({last})")


def to_samples(mp3, tempo=1.0):
    """Decode to 48 kHz mono int16, trimming the silence edge-tts pads around speech."""
    trim = "silenceremove=start_periods=1:start_threshold=-50dB"
    af = f"{trim},areverse,{trim},areverse"
    if abs(tempo - 1.0) > 0.005:
        af += f",atempo={tempo:.4f}"
    wav = mp3 + ".wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-af", af,
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", wav])
    with wave.open(wav, "rb") as w:
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
    os.remove(wav)
    return a


async def synth_all(segs, tmp, speed=1.0):
    sem = asyncio.Semaphore(3)

    async def one(i, s):
        async with sem:
            s["mp3"] = os.path.join(tmp, f"seg{i:04d}.mp3")
            rate = ((1 + s["rate"] / 100) * speed - 1) * 100
            await tts(s["text"], s["edge"], rate, s["pitch"], s["mp3"])
            s["pcm"] = to_samples(s["mp3"])

    res = await asyncio.gather(*(one(i, s) for i, s in enumerate(segs)), return_exceptions=True)
    failed = [r for r in res if isinstance(r, Exception)]
    if failed:
        other = [r for r in failed if not isinstance(r, SpeechError)]
        if other:
            raise other[0]
        raise SpeechError(f"{len(failed)} of {len(segs)} lines got no audio from the speech "
                          f"service, e.g. {failed[0]}")


# ---------- timeline ----------

def fit_and_place(segs, timed, video_dur, max_speed, gap, tmp):
    """Give every segment a real start time, speeding speech up when a slot is too short."""
    warnings = []
    if not timed:
        total = sum(len(s["pcm"]) for s in segs) / SR + gap * (len(segs) - 1)
        if total > video_dur:
            f = min(max_speed, total / video_dur * 1.02)
            asyncio.run(synth_all(segs, tmp, speed=f))
    cursor = 0.0
    for i, s in enumerate(segs):
        start = max(s.get("start", cursor), cursor) if timed else cursor
        if timed:
            nxt = segs[i + 1]["start"] if i + 1 < len(segs) else max(video_dur, s.get("end", 0))
            avail = max(nxt - start - 0.05, 0.3)
            dur = len(s["pcm"]) / SR
            if dur > avail:
                f = min(max_speed, dur / avail * 1.03)
                rate = ((1 + s["rate"] / 100) * f - 1) * 100
                asyncio.run(tts(s["text"], s["edge"], rate, s["pitch"], s["mp3"]))
                s["pcm"] = to_samples(s["mp3"])
                dur = len(s["pcm"]) / SR
                if dur > avail:  # small residual: time-stretch instead of spilling over
                    s["pcm"] = to_samples(s["mp3"], tempo=min(1.12, dur / avail))
                    dur = len(s["pcm"]) / SR
                if dur > avail + 0.15:
                    warnings.append(f"segment {i + 1} at {start:.1f}s runs {dur - avail:.1f}s "
                                    f"over its slot - shorten: \"{s['text'][:40]}\"")
        s["t0"] = start
        s["t1"] = start + len(s["pcm"]) / SR
        cursor = s["t1"] + (gap if not timed else 0.05)
    return warnings


def write_track(segs, total_dur, path):
    buf = array.array("h", bytes(2 * int(total_dur * SR + 1)))
    for s in segs:
        a = int(s["t0"] * SR)
        buf[a:a + len(s["pcm"])] = s["pcm"]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(buf.tobytes())


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segs, 1):
            f.write(f"{i}\n{srt_time(s['t0'])} --> {srt_time(s['t1'])}\n{s['text']}\n\n")


# ---------- final mux ----------

def mux(video, track, out, mode, has_audio, bg_volume, voice_gain, extend, srt, font):
    fc = [f"[1:a]volume={voice_gain}[v]"]
    if not has_audio or mode == "mute":
        fc.append("[v]alimiter=limit=0.95[a]")
    elif mode == "duck":  # original dips only while the narrator speaks (good for music)
        fc += ["[v]asplit[v1][v2]",
               "[0:a][v1]sidechaincompress=threshold=0.02:ratio=15:attack=15:release=400[bg]",
               "[bg][v2]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]"]
    else:  # low = constant quiet bed (good over original speech); keep = untouched
        vol = 1.0 if mode == "keep" else bg_volume
        fc += [f"[0:a]volume={vol}[bg]",
               "[bg][v]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]"]
    vf = []
    if extend > 0.2:  # narration outlasts the picture: hold the last frame
        vf.append(f"tpad=stop_mode=clone:stop_duration={extend:.2f}")
    if srt:
        esc = srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        # libass sizes text relative to frame height, so a size that suits 16:9
        # fills half the screen on a vertical 9:16 reel - shrink it there.
        dims = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                    "stream=width,height", "-of", "csv=p=0", video]).strip().split(",")
        portrait = int(dims[1]) > int(dims[0])
        size, margin = (11, 48) if portrait else (20, 28)
        style = f"FontName={font},FontSize={size},Outline=1,MarginV={margin}"
        vf.append(f"subtitles='{esc}':force_style='{style}'")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", video, "-i", track]
    if vf:
        fc.append(f"[0:v]{','.join(vf)}[vo]")
        cmd += ["-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "copy"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    run(cmd)


def thai_font():
    try:
        out = subprocess.run(["fc-list", ":lang=th", "family"], capture_output=True, text=True).stdout
        fams = [l.split(",")[0].strip() for l in out.splitlines() if l.strip()]
        for pref in ("Sarabun", "Noto Sans Thai", "Kanit", "Prompt", "Loma", "Garuda", "Tahoma"):
            if pref in fams:
                return pref
        if fams:
            return fams[0]
    except FileNotFoundError:
        pass
    return "Tahoma"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?")
    ap.add_argument("script", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("--voice", help="voice preset (see --list-voices); overrides the script default")
    ap.add_argument("--original", choices=["low", "duck", "mute", "keep"], default="low",
                    help="what to do with the video's own sound (default: low)")
    ap.add_argument("--bg-volume", type=float, default=0.12, help="original volume in 'low' mode")
    ap.add_argument("--voice-gain", type=float, default=1.0)
    ap.add_argument("--rate", type=float, default=0,
                    help="speaking pace in %% on top of the preset, e.g. -8 = calmer, 8 = brisker")
    ap.add_argument("--max-speed", type=float, default=1.3, help="max speed-up used to fit a slot")
    ap.add_argument("--gap", type=float, default=0.35, help="pause between lines of an untimed script")
    ap.add_argument("--burn-subs", action="store_true", help="burn Thai subtitles into the picture")
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--sample", metavar="TEXT", help="just speak TEXT to the -o audio file")
    a = ap.parse_args()
    voices = load_voices()

    if a.list_voices:
        for k, v in voices.items():
            print(f"{k:14s} {v['label']}")
        return
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required but not installed.")

    if a.sample:
        edge, rate, pitch = resolve_voice(a.voice, voices)
        out = a.output or "sample.mp3"
        asyncio.run(tts(a.sample, edge, rate, pitch, out))
        print(f"Wrote {out}")
        return

    if not (a.video and a.script and a.output):
        ap.error("VIDEO, SCRIPT and -o OUTPUT are required")
    video_dur, has_audio = probe(a.video)
    default_voice, segs, timed = load_script(a.script)
    if not segs:
        sys.exit("The script has no text to speak.")
    if timed:
        segs.sort(key=lambda s: s["start"])
    for s in segs:
        s["edge"], s["rate"], s["pitch"] = resolve_voice(
            s.get("voice") or a.voice or default_voice, voices)
        s["rate"] += a.rate

    with tempfile.TemporaryDirectory() as tmp:
        print(f"Synthesizing {len(segs)} lines...")
        asyncio.run(synth_all(segs, tmp))
        warnings = fit_and_place(segs, timed, video_dur, a.max_speed, a.gap, tmp)
        end = segs[-1]["t1"]
        track = os.path.join(tmp, "narration.wav")
        write_track(segs, max(video_dur, end), track)
        srt_path = os.path.splitext(a.output)[0] + ".th.srt"
        write_srt(segs, srt_path)
        mux(a.video, track, a.output, a.original, has_audio, a.bg_volume, a.voice_gain,
            end - video_dur, srt_path if a.burn_subs else None, thai_font())

    out_dur, _ = probe(a.output)
    print(f"Wrote {a.output} ({out_dur:.1f}s; source {video_dur:.1f}s) and {srt_path}")
    if end - video_dur > 0.2:
        print(f"NOTE: narration is {end - video_dur:.1f}s longer than the video; last frame was held.")
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    try:
        main()
    except SpeechError as e:
        sys.exit(f"Speech synthesis failed: {e}\n"
                 "Finished lines are cached - run the same command again to resume. If every "
                 "line fails, check that the machine can reach speech.platform.bing.com.")
