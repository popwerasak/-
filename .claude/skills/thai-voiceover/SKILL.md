---
name: thai-voiceover
description: Add a natural-sounding Thai voice-over (ลงเสียงพากย์ไทย / พากย์เสียง / ใส่เสียงบรรยาย) to a video using realistic male and female Thai neural voices, and return the finished video file. Use this whenever the user gives a video (mp4, mov, etc.) and wants Thai narration, dubbing, พากย์ไทย, เสียงบรรยาย, เสียงผู้ชาย/ผู้หญิง, or to turn a script, subtitle file or foreign-language clip into spoken Thai - even if they only say "ลงเสียงให้หน่อย" or "ทำเสียงต่อให้" next to a video. Also use it to produce Thai speech audio alone (voice samples, narration mp3).
---

# Thai voice-over (ลงเสียงพากย์ไทย)

Turn a video plus a Thai script into a finished video with a spoken Thai track.
The bundled `scripts/dub.py` does the speech synthesis, timing and mixing; your
job is to get a good Thai script with sensible timings, pick the voice, run it,
check the result and hand the file back. Reply to the user in Thai.

The voices are Microsoft neural Thai voices reached through the free `edge-tts`
package (no API key). They sound like real people, but they are synthetic - say
so if the user asks whether a human recorded them.

## Voices

| Preset | เสียง | Good for |
|---|---|---|
| `female` (default) | หญิง อบอุ่น เป็นกันเอง | ทั่วไป |
| `male` | ชาย สุภาพ น่าเชื่อถือ | ทั่วไป |
| `female-bright` | หญิงสดใส | รีวิว โฆษณา |
| `female-calm` | หญิงนุ่ม ช้า | สารคดี สุขภาพ |
| `male-deep` | ชายทุ้ม | สารคดี เล่าเรื่อง |
| `male-bright` | ชายกระฉับกระเฉง | รีวิว ข่าวสั้น |

Thai aliases work too (`ชาย`, `หญิง`, `ชายทุ้ม`, ...). Presets live in
`scripts/voices.json`; add a new one there if the user wants a different feel
(rate in %, pitch in Hz). If the user did not say male or female, use `female`
and mention they can switch - don't stop to ask.

Match the polite particles to the voice: ครับ for male voices, ค่ะ/คะ for female.
A male voice saying "ค่ะ" is the most common thing that makes a dub sound wrong.

## Setup (once per session)

```bash
pip install -q edge-tts          # speech
ffmpeg -version | head -1        # must exist
```

Synthesis needs to reach `speech.platform.bing.com`. The free service is
sometimes slow: it can refuse one particular line for a minute or two, so
`dub.py` keeps retrying for up to three minutes per line (run it with a
generous timeout, or in the background for long scripts). Every finished line
is cached in `~/.cache/thai-voiceover`, so if a run does fail, running the same
command again resumes instead of starting over, and re-running after editing a
few lines only re-voices those lines. If every line fails, the host is probably
blocked - tell the user it has to be allowed; don't swap in a robotic offline
voice without saying so.

## Workflow

### 1. Look at the video

`ffprobe` it for duration and whether it has sound. Then work out where the
script comes from:

- **The user gave a Thai script** (text in chat, `.txt`, `.srt`) → use it.
- **The video has speech to dub** (foreign language, or Thai to re-voice) →
  transcribe it: `pip install -q faster-whisper` then
  `python scripts/transcribe.py VIDEO -o segments.json`. This gives timed
  segments in the original language for you to translate. It downloads a model
  from huggingface.co; if that is blocked, ask the user for the script or
  subtitles instead.
- **No speech and no script** → extract a frame every few seconds
  (`ffmpeg -i VIDEO -vf fps=1/3 frames/%03d.jpg`), look at them, and write a
  narration that describes what is on screen. Show the user the script in your
  final message so they can ask for changes.

### 2. Write the Thai script

Write for the ear, not the page: short spoken sentences, natural word choice,
numbers and abbreviations spelled the way they should be said if the reading
could be ambiguous (e.g. "3-5 ครั้ง" → "สามถึงห้าครั้ง"). Add ๆ and spaces
between clauses - the voice pauses at spaces, which is what makes it sound human.

When translating a dub, translate the meaning, not word for word, and keep each
line short enough to say in its time slot. Thai speech runs at roughly 12-14
characters per second; a line much longer than `slot_seconds × 13` will be
sped up and sound rushed, so trim it.

Save the script as JSON when you have timings (several speakers can each get
their own voice):

```json
{"voice": "female",
 "segments": [
  {"start": 0.5, "end": 4.0, "text": "สวัสดีค่ะ วันนี้เราจะมาดูวิธีดูแลสุขภาพง่ายๆ"},
  {"start": 5.0, "end": 9.0, "voice": "male", "text": "เริ่มจากการดื่มน้ำให้เพียงพอครับ"}
 ]}
```

Without timings, save a `.txt` with one sentence or phrase per line; the lines
are spoken back to back from the start of the video. An `.srt` is also accepted
and spoken at its own timestamps.

### 3. Run it

```bash
python scripts/dub.py VIDEO script.json -o OUTPUT.mp4 --voice female --original low
```

`--original` decides what happens to the sound already in the video:

- `low` (default) - original kept as a quiet bed. Right for dubbing over
  someone speaking another language.
- `duck` - original at full volume, dipping only while the narrator talks.
  Right for videos with music or ambience and no speech.
- `mute` - narrator only. Right when the original is the same speech being replaced
  and the user wants it gone.
- `keep` - original untouched underneath.

Other useful flags: `--burn-subs` (burn Thai subtitles into the picture - only
when asked, it re-encodes the video), `--voice-gain 1.3` (louder narrator),
`--bg-volume 0.2`, `--max-speed 1.3`, `--rate -8` (calmer pace; use when the user says
the voice is too fast - and also give each line a longer slot, because a line
that overflows its slot gets sped up again).

The script always writes `OUTPUT.th.srt` next to the video with the real spoken
timings. The picture is copied untouched unless subtitles are burned in or the
narration runs past the end (then the last frame is held).

### 4. Check before handing over

Read the script's output. A `WARNING: segment N ... over its slot` means that
line is too long for its gap: shorten that line's text and run again rather
than delivering a dub that drifts out of sync. A `NOTE` about the narration
being longer than the video means the script as a whole is too long - tighten
it unless the user is happy with a held last frame.

Then give the user the output video (and mention the `.srt`), say which voice
was used and which other voices they can ask for.

## Voice samples only

```bash
python scripts/dub.py --sample "สวัสดีครับ ยินดีต้อนรับ" --voice male -o sample.mp3
python scripts/dub.py --list-voices
```

Pre-made samples of every preset are in `assets/samples/` if the user wants to
hear the choices first.
