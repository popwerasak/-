#!/usr/bin/env python3
"""Voice a scene-based video and cut each scene down to its narration plus a short gap.

Use this when the user wants the dead air between lines removed ("ตัดช่องไฟออก").
Each scene keeps its own picture from its start; only its tail is trimmed, so the
on-screen captions still match the voice. The original sound (music/ambience) is
laid underneath continuously instead of being chopped at every cut.

Usage:
  tighten.py VIDEO script.json -o OUT.mp4 [--gap 0.5] [--lead 0.3] [--tail 0.8]
             [--rate -4] [--original duck|low|mute] [--fade 0.8]

script.json is the same format as dub.py, where each segment's "start" is the
time its scene begins in the source video:
  {"voice": "male-deep", "segments": [{"start": 0, "text": "..."}, ...]}
A segment may set "end" to mark where its scene ends in the source; otherwise the
next segment's start (or the video's end) is used.
"""
import argparse
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dub  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("script")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--rate", type=float, default=0, help="pace in %% on top of the preset")
    ap.add_argument("--gap", type=float, default=0.5, help="silence after each line before the next scene")
    ap.add_argument("--lead", type=float, default=0.3, help="silence before the first line")
    ap.add_argument("--tail", type=float, default=0.8, help="silence after the last line")
    ap.add_argument("--fade", type=float, default=0.8, help="fade-out at the very end (0 = none)")
    ap.add_argument("--original", choices=["duck", "low", "mute"], default="duck")
    ap.add_argument("--bg-volume", type=float, default=0.12)
    a = ap.parse_args()

    voices = dub.load_voices()
    src_dur, has_audio = dub.probe(a.video)
    default_voice, segs, timed = dub.load_script(a.script)
    if not segs or not timed:
        sys.exit("tighten.py needs a JSON/SRT script where every segment has a start time.")
    segs.sort(key=lambda s: s["start"])
    for s in segs:
        s["edge"], s["rate"], s["pitch"] = dub.resolve_voice(
            s.get("voice") or a.voice or default_voice, voices)
        s["rate"] += a.rate

    with tempfile.TemporaryDirectory() as tmp:
        print(f"Synthesizing {len(segs)} lines...")
        asyncio.run(dub.synth_all(segs, tmp))

        # Build the cut list: each scene plays from its source start for lead+speech+gap.
        cuts, t = [], 0.0
        warnings = []
        for i, s in enumerate(segs):
            src_end = s.get("end") or (segs[i + 1]["start"] if i + 1 < len(segs) else src_dur)
            speech = len(s["pcm"]) / dub.SR
            pre = a.lead if i == 0 else 0.0
            post = a.tail if i == len(segs) - 1 else a.gap
            want = pre + speech + post
            avail = src_end - s["start"]
            if want > avail:  # scene too short: hold its last frame for the rest
                warnings.append(f"scene {i + 1} is {want - avail:.1f}s shorter than its line; "
                                "its last frame is held")
            cuts.append((s["start"], min(want, avail), max(0.0, want - avail)))
            s["t0"] = t + pre
            s["t1"] = s["t0"] + speech
            t += want
        total = t

        # Video: trim + concat the scene pieces.
        fc, labels = [], []
        for i, (st, dur, hold) in enumerate(cuts):
            chain = f"[0:v]trim=start={st:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS"
            if hold > 0.01:
                chain += f",tpad=stop_mode=clone:stop_duration={hold:.3f}"
            fc.append(chain + f"[p{i}]")
            labels.append(f"[p{i}]")
        vchain = f"{''.join(labels)}concat=n={len(cuts)}:v=1:a=0"
        if a.fade > 0:
            vchain += f",fade=t=out:st={total - a.fade:.3f}:d={a.fade:.3f}"
        fc.append(vchain + ",format=yuv420p[vo]")

        # Render picture and sound separately: trimming one input many times while
        # also reading its audio in the same graph makes ffmpeg drop audio.
        vid = os.path.join(tmp, "video.mp4")
        dub.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-filter_complex", ";".join(fc),
                 "-map", "[vo]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", vid])

        # Audio: narration track + continuous original bed.
        track = os.path.join(tmp, "narration.wav")
        dub.write_track(segs, total, track)
        af = ["[1:a]aformat=sample_rates=48000:channel_layouts=stereo[v]"]
        if has_audio and a.original != "mute":
            bed = (f"[0:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                   f"aformat=sample_rates=48000:channel_layouts=stereo")
            if a.fade > 0:
                bed += f",afade=t=out:st={total - a.fade:.3f}:d={a.fade:.3f}"
            if a.original == "low":
                af.append(bed + f",volume={a.bg_volume}[bg]")
                af.append("[bg][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
            else:
                af.append(bed + "[bg0]")
                af.append("[v]asplit[v1][v2]")
                af.append("[bg0][v1]sidechaincompress=threshold=0.02:ratio=15:attack=15:release=400[bg]")
                af.append("[bg][v2]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
        else:
            af.append("[v]alimiter=limit=0.95[a]")
        aud = os.path.join(tmp, "mix.wav")
        dub.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-i", track,
                 "-filter_complex", ";".join(af), "-map", "[a]", aud])

        dub.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", aud, "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}",
                 "-movflags", "+faststart", a.output])
        srt = os.path.splitext(a.output)[0] + ".th.srt"
        dub.write_srt(segs, srt)

    print(f"Wrote {a.output} ({total:.1f}s, was {src_dur:.1f}s) and {srt}")
    for i, (st, dur, hold) in enumerate(cuts):
        print(f"  scene {i + 1}: source {st:.2f}s +{dur:.2f}s -> line at {segs[i]['t0']:.2f}-{segs[i]['t1']:.2f}s")
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    try:
        main()
    except dub.SpeechError as e:
        sys.exit(f"Speech synthesis failed: {e}\nFinished lines are cached - run again to resume.")
