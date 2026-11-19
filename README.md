# GTA 6 Clipper

Two macOS skills for Codex and Claude Code that turn GTA 6 streams into ready-to-post vertical clips.

- **gta6-clipper** clips a stream that has finished. Give it a YouTube, Twitch or Kick link, or nothing and it finds today's biggest GTA 6 streams.
- **gta6-live-clipper** clips a stream while it's still live. A clip is ready about 5 to 8 minutes after the moment happens.

Every clip comes out 1080x1920: facecam on top, gameplay below, a hook title, word-by-word captions, and a post caption with hashtags.

**Mac version.** On Windows? Use the Windows version: https://github.com/vossashtonai/gta6-clipper-windows
or paste this in PowerShell: `irm https://raw.githubusercontent.com/vossashtonai/gta6-clipper-windows/main/install.ps1 | iex`

## Use in Codex

Open this repository as your Codex workspace. The two links in `.agents/skills/`
register the existing skill folders with Codex. Start a new Codex chat in this
workspace if an existing chat does not show them.

- `$gta6-clipper set up the GTA 6 clipper` installs the shared macOS dependencies. Wait for `READY`.
- `$gta6-clipper clip this stream <VOD URL>` selects and renders up to three highlights.
- `$gta6-live-clipper clip this stream live <live URL>` keeps the recorder and highlight selection running in the active chat.

In Codex, outputs go under the repository's `runs/` folder by default.
Each clip has an MP4 and a companion text file with a title, caption, and hashtags.

## Install in Claude Code

### Option A: paste this into Claude Code (easiest)

```text
Install the GTA 6 Clipper skills from https://github.com/vossashtonai/gta6-clipper.
Clone the repo to a temporary folder, then copy BOTH folders inside its skills/ folder
(gta6-clipper and gta6-live-clipper) into ~/.claude/skills/ so they sit side by side.
Then run: bash ~/.claude/skills/gta6-clipper/scripts/setup.sh
Tell me what it installed and whether it says READY. Then remind me to restart Claude Code.
```

### Option B: as a Claude Code plugin

In Claude Code:

```text
/plugin marketplace add vossashtonai/gta6-clipper
/plugin install gta6-clipper@ashtonvossai
```

Then say **set up the GTA 6 clipper**.

### Option C: by hand

```bash
git clone https://github.com/vossashtonai/gta6-clipper.git /tmp/gta6-clipper
cp -R /tmp/gta6-clipper/skills/gta6-clipper /tmp/gta6-clipper/skills/gta6-live-clipper ~/.claude/skills/
bash ~/.claude/skills/gta6-clipper/scripts/setup.sh
```

Setup checks what your Mac needs and installs what's missing: Homebrew packages (FFmpeg, whisper-cpp, Deno), a Python environment (yt-dlp, OpenCV, Pillow) and the Whisper speech model (~465 MB). Re-run it any time downloads start failing; it updates yt-dlp.

## Use it

Open Claude Code and say:

- **clip this stream** `<link>`
- **find me today's biggest GTA 6 streams and clip them**
- **live clip** `<link>` (for a stream that's live right now)

Clips land in `~/GTA6-Clips/`. Each one has an `.mp4` and a `.txt` with the title, caption and hashtags.

## Terminal commands

Run `make help` from the repository root for all setup, VOD, live, thumbnail,
and publishing commands. Make uses `runs/` for VODs and `runs/live/` for live
recordings by default. Set `GTA6_CLIPS_DIR` or `GTA6_LIVE_DIR` to use other folders.

```sh
make setup
make discover ARGS='--limit 5'
make prep URL='https://www.youtube.com/watch?v=VIDEO_ID'
make status RUN='runs/example'
make render RUN='runs/example' ARGS='--top 3'

make setup-upload
make upload-preview
make upload
```

Highlight selection is handled by the clipper skill or by editing pick files
before running `make render` or `make live-clip`. Pass additional CLI flags
and multiple positional inputs with `ARGS`. Quote paths individually inside it,
for example `make thumbnail ARGS='"path/to/first clip.mp4" "path/to/second clip.mp4" --at 1'`.

## How it works

| Step | Finished stream | Live stream | Tools |
|---|---|---|---|
| 1. Get the stream | Downloads the audio only (4 h ≈ 220 MB) | Records 1-minute pieces, keeps the last 15 min | yt-dlp, FFmpeg |
| 2. Speech to text | Whole stream in one go | Each minute as it lands | FFmpeg, Whisper |
| 3. Find the hype | Loud seconds + YouTube replay chat speed | Loud seconds + live Twitch chat speed | FFmpeg, chat |
| 4. Pick the moments | Claude reads 12-min chunks, best 3 scoring 7+ | Claude reads each 5-min window, any 7.5+ | Claude Code |
| 5. Make the clip | Downloads only those minutes | Cuts from the pieces already on your Mac | OpenCV, Whisper, Pillow, FFmpeg |

Chat is counted, never read: 10-second buckets, a spike is 8+ messages at 2.5x the normal rate. Loud means 9 dB above the streamer's own normal. The facecam is found by looking for a face, and box edges, that stay still while the gameplay moves.

## Run it free

Picking (step 4) is the only part that uses AI. Everything else runs on your Mac. To run without a Claude subscription:

1. Install [Ollama](https://ollama.com).
2. Check your memory (Apple menu → About This Mac → Memory). 16 GB: `ollama pull qwen3.5:9b`. 32 GB or more: `ollama pull qwen3.5:27b`.
3. In Terminal: `ollama launch claude` and pick the model.
4. Same prompts as above.

The free model is slower and its picks are rougher than Claude's. Expect some back and forth.

## Good to know

- Age-restricted YouTube streams and Kick need your browser login. Tell Claude to use `--cookies chrome`.
- YouTube streams that are still live can be clipped by the finished-stream skill once the replay is up. Twitch past broadcasts work while the stream is still going.
- Twitch in "find me streams" is optional: create a free app at [dev.twitch.tv/console](https://dev.twitch.tv/console) and put `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` in `skills/gta6-clipper/.env` (see `.env.example`).
- Live clipping needs the Claude Code session to stay open, and run at most 2 streams at once on a 16 GB Mac.
- Clip streamers who are fine with clipping, and watch every clip before you post it.
- YouTube ad money needs the Partner Program, and YouTube can refuse it for reposted, mass-made content. Add something of your own.

## Made by

[Ashton Voss AI](https://www.youtube.com/@ashtonvossai). More free AI systems in the AI Alliance Community.

MIT licensed.

## Upload approved clips

Run `python -m upload.tui` to review runs and publish approved clips to configured
YouTube, Facebook Page, and Instagram destinations. See the [upload setup guide](upload/README.md).
