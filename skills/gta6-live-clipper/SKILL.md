---
name: gta6-live-clipper
description: Capture and clip a currently live YouTube, Twitch, or Kick stream on macOS using a rolling buffer. Use when the user wants highlights while the stream is still running. Use gta6-clipper for finished streams or VODs.
---

# GTA 6 LIVE Clipper

Same engine and output as the `gta6-clipper` skill (needs that one set up first, it shares its venv,
models and render code). The difference: nothing gets downloaded twice. The live stream is recorded into
1-minute segments on this Mac, only the last `--buffer-min` minutes are kept, and clips are cut from them.

`L` = this skill's folder, `V` = the gta6-clipper folder next to it. Run:
`"$V/.venv/bin/python" "$L/scripts/live.py" <command>`. Resolve the skill directory to its real path before locating its sibling. Quote all paths.
In Codex, set `GTA6_LIVE_DIR` to an absolute workspace path such as `<repo>/runs/live`.
Use the same location throughout the run.

If it says "Set up the GTA 6 clipper first", run `bash "$V/scripts/setup.sh"`.

## 1. Start

`start <url> [<url> ...]`: Twitch channel (`https://www.twitch.tv/kaicenat`), YouTube live link, or Kick.
Options: `--quality 720` (default; 1080 doubles disk), `--buffer-min 15`, `--window-min 5`,
`--cookies chrome` (Kick, age-restricted YouTube, with user authorization to access browser cookies). Each stream gets a background recorder and a run folder.
Max 2 streams on a 16 GB Mac (each transcribes a minute of audio every minute). If it says NOT LIVE, the
stream is finished: use gta6-clipper.

## 2. The loop (you run this until the stream ends or the user says stop)

Read `$V/references/picking.md` once before the first window. Then repeat:

1. `next <run> [<run> ...]` prints the next window and the path for its picks file. In Codex, use
   `next <run> [<run> ...] --wait 45` and poll the command session if it yields.
2. Write `picks/window_NNN.json` in THAT run folder, same format and same harsh rules as picking.md.
   `[]` when nothing qualifies (most windows). Windows overlap by 45 s: don't pick the same moment twice.
3. If you wrote any pick with score >= 7.5, run `clip <run>` right away. It renders from the buffer,
   skips anything already clipped, and prints the new clip paths.
4. List each new clip with a stable number, title, and clickable MP4 link. Follow
   [clip review and upload](../gta6-clipper/references/upload.md) and ask which clips to approve and
   where to send them. Keep capturing and clipping while the user reviews. Use a nonblocking
   question when available, and keep the clip numbers stable for later replies. Skip empty windows.

`next` printing "NO NEW WINDOW YET" just means keep looping. "STREAM ENDED" means run `clip` once more,
then report and offer any clips that still need a decision for review. Live clip bar is 7.5
(not 7): posting fast only matters if the clip is good.

Clips are ready ~5-8 min after the moment: up to 5 min for the window to close + picking + ~1 min render.
For a faster cadence use `--window-min 3` (more reads, more tokens).

## 3. Stop / check

- `status <run>`: recorder alive, minutes recorded, windows waiting, clips made.
- `stop <run>`: stops the recorder (the last partial window still gets written: pick it and clip).
- Clips live in `<run>/clips/` (mp4 + txt with title, caption, hashtags). Provide clickable links to the output files.
- The buffer deletes itself as it rolls; old runs in `~/GTA6-Clips/live/` only get deleted if the user says so.

## Notes

- Chat speed is tracked on Twitch (read-only anonymous chat). YouTube/Kick live use loudness only.
- A moment older than the buffer can't be clipped (prints "out of buffer"). Keep up with the windows.
- Keep the agent session active to score windows and render clips as they arrive.
