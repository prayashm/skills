---
name: yesno-label
description: Serve a one-card-at-a-time yes/no (or Model A/Model B/Neither) video labelling page (big ✗/✓ buttons, arrow keys, drag or swipe to answer) and collect the answers as JSONL. Use when a set of clips needs a quick human yes/no judgement, such as "is this crop correct", "is this slow motion", "is this live or a replay", or when asked for Prodigy-style binary annotation, a swipe/tinder labeller, an A/B comparison of two model outputs, or ground truth labels for a video classifier.
---

# yesno-label

One question, many videos, one card at a time. The user answers yes, no or unsure;
each answer is appended to a JSONL file. Use this instead of Label Studio, Prodigy or
a custom page: the single-decision card is the point.

The tool is `scripts/yesno.py` (Python 3.9+, stdlib only, page embedded). It is not
for ranking more than two variants of the same clip.

## Run

```bash
python3 scripts/yesno.py "Is this slow motion?" clips/*.mp4 --out /abs/path/slowmo.jsonl --port 8765
```

- Videos are local paths or `http(s)://` URLs (CDN URLs must allow cross-origin playback).
  Local files are served as MP4 with byte ranges, so Safari plays them.
- One question per run. For several questions about the same clips, run once per
  question with a separate `--out` each.
- Use an absolute `--out` path, and keep it next to the experiment (not `/tmp`) when the
  labels are ground truth.
- It binds 127.0.0.1. Run it in the background and give the user the URL. To label on a
  phone, put it behind something like `tailscale serve --bg --https=<port> <port>`; avoid
  exposing it to the public internet, since it has no auth.
- Restarting with the same `--out` resumes at the first unanswered video.
- `--choices "Model A,Model B,Neither"` relabels the buttons as left,right,middle
  (default `no,yes,unsure`) for A/B or option picks; `answer` stores the choice text.
  Each card is still one video, so for A/B render the pair side by side first, with
  A on the left (for example `ffmpeg -i a.mp4 -i b.mp4 -filter_complex hstack pair.mp4`):
  the card tags its left and right corners with the two names. Custom choices use
  neutral grey instead of red/green, and summary thumbnails show the whole frame
  instead of cropping to 16:9.

## What the user sees

- Video loops on a card. → or `y` yes, ← or `n` no, ↓ or `u` unsure, backspace goes
  back one card, space toggles 0.25x/1x (for slow-mo calls).
- Dragging the card (mouse or touch) tilts and tints it; past 100 px it answers.
- When every video is answered, a summary shows the counts and a thumbnail grid;
  clicking a thumbnail reopens that card to change the answer.
- On the summary, `c` (or clicking the "c copy JSONL" hint) copies the answers to the
  clipboard, one line per video, already deduped; the saved-to path pulses green to
  confirm, and a red toast shows only if the copy failed. Without https it falls back
  to the browser's legacy copy.

## Output

One line per answer, last answer per `video` wins:

```json
{"video": "/abs/clips/5.mp4", "answer": "yes", "question": "Is this slow motion?", "ts": 1794288657.4}
```

Read it with a dict keyed on `video`, not a list, or re-answers double count. When
reporting results, compare against any earlier labels for the same clips and flag
disagreements instead of silently overwriting ground truth.

## Finish

When the user says they are done: show the answers as a table, stop the server
(`lsof -ti tcp:<port> | xargs kill`), and remove any share you set up. Confirm both
are gone.

## Checking a change to the page

The UI is inline in `PAGE` in `yesno.py`, a non-raw Python string, so write a JS `\n`
as `\\n`. After editing, run it on two or three clips, drive it headless (Playwright or
similar: arrow keys, a mouse drag, a screenshot, console errors), then confirm the JSONL
line was written. Style is shadcn zinc dark tokens with a spring drag; keep radii at
shadcn defaults.
