"""Review and publish finished GTA 6 clips from the terminal."""
import argparse
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import subprocess

from dotenv import dotenv_values
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

from .facebook import upload as facebook
from .instagram import upload as instagram
from .meta import PublishError, settings
from .youtube import upload as youtube
from .youtube.thumbnail import generate


ROOT = youtube.DEFAULT_ENV.parent


@dataclass(frozen=True)
class Video:
    path: Path
    seconds: float
    short: bool


def discover(roots):
    runs = defaultdict(set)
    seen = set()
    for root in roots:
        for path in sorted(root.rglob("*.mp4")):
            if path.parent.name != "clips" or not path.is_file():
                continue
            clip = path.resolve()
            if clip in seen:
                continue
            seen.add(clip)
            parts = path.relative_to(root).parts
            depth = 2 if parts[0] == "live" and len(parts) >= 4 else 1
            run = root.joinpath(*parts[:depth]) if len(parts) > 2 else root
            runs[run].add(clip)
    return {run: sorted(paths) for run, paths in sorted(runs.items())}


def probe(path):
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration:stream=width,height,sample_aspect_ratio:stream_side_data=rotation",
        "-of", "json", str(path),
    ])
    info = json.loads(output)
    video = info["streams"][0]
    seconds = float(info["format"]["duration"])
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Invalid video duration")
    width, height = video["width"], video["height"]
    sar = video.get("sample_aspect_ratio")
    if sar and sar not in {"N/A", "0:1"}:
        numerator, denominator = map(int, sar.split(":"))
        width *= numerator
        height *= denominator
    rotation = next((entry["rotation"] for entry in video.get("side_data_list", [])
                     if "rotation" in entry), 0)
    if int(rotation) % 180 == 90:
        width, height = height, width
    return Video(path, seconds, width <= height and seconds <= 180)


def display(value):
    return "".join(char for char in str(value) if char.isprintable() or char == "\n")


def choose(prompt, choices, multiple=False):
    for index, (label, _) in enumerate(choices, 1):
        print(f"  {index}. {display(label)}")
    suffix = " (numbers separated by commas, all, or q)" if multiple else " (number or q)"
    while True:
        raw = input(prompt + suffix + " > ").strip().lower()
        if raw == "q":
            raise EOFError()
        if raw == "all" and multiple:
            return [value for _, value in choices]
        try:
            indexes = list(dict.fromkeys(int(part) - 1 for part in raw.split(",")))
            if all(0 <= index < len(choices) for index in indexes) and (multiple or len(indexes) == 1):
                selected = [choices[index][1] for index in indexes]
                return selected if multiple else selected[0]
        except ValueError:
            pass
        print("Choose from the numbers shown.")


def destinations(config, videos):
    choices = []
    if all(config.get(key) for key in youtube.ENV_KEYS):
        choices.append(("YouTube", youtube))
    if all(config.get(key) for key in facebook.ENV_KEYS):
        account, _, _ = settings(config, facebook.ENV_KEYS)
        choices.append((f"Facebook Page {account} (publishes to Page)", facebook))
    if all(config.get(key) for key in instagram.ENV_KEYS) and all(
        video.short and video.seconds >= 3 for video in videos
    ):
        account, _, _ = settings(config, instagram.ENV_KEYS)
        choices.append((f"Instagram account {account} (publishes Reels)", instagram))
    return choices


def publish_batch(config, selections, targets, privacy):
    prepared = []
    for video, title, description in selections:
        try:
            generate(video.path, min(1, video.seconds / 2))
            prepared.append((video, title, description))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            print(f"{display(video.path.name)}: thumbnail failed ({error})")
    failed = len(prepared) != len(selections)
    with ExitStack() as stack:
        client = None
        for label, target in targets:
            for video, title, description in prepared:
                try:
                    if target is youtube:
                        if client is None:
                            client = stack.enter_context(youtube.client_from_config(config))
                        youtube.upload(client, video.path, youtube.video_body(title, description, privacy, False))
                    else:
                        print(target.publish(config, video.path, title, description))
                except (PublishError, OSError, ValueError, GoogleAuthError, HttpError) as error:
                    failed = True
                    # OAuth and HTTP exceptions may contain request details.
                    detail = type(error).__name__ if isinstance(error, (GoogleAuthError, HttpError)) else str(error)
                    print(f"{label}: {display(video.path.name)}: {display(detail)}")
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", action="append", type=Path, help="Search root (repeatable)")
    parser.add_argument("--env-file", type=Path, default=youtube.DEFAULT_ENV)
    parser.add_argument("--dry-run", action="store_true", help="Review the batch without publishing")
    args = parser.parse_args()
    config = dotenv_values(args.env_file, interpolate=False)
    roots = args.runs_dir or [
        ROOT / "runs",
        Path(os.getenv("GTA6_CLIPS_DIR", Path.home() / "GTA6-Clips")),
        Path(os.getenv("GTA6_LIVE_DIR", Path.home() / "GTA6-Clips" / "live")),
    ]
    try:
        runs = discover([root.expanduser().resolve() for root in roots])
        if not runs:
            parser.exit(1, "No finished MP4s found in run clips folders. Try --runs-dir.\n")
        selected_runs = choose("Select runs", [
            (f"{run} ({len(paths)} videos)", run) for run, paths in runs.items()
        ], multiple=True)
        videos = []
        for run in selected_runs:
            for path in runs[run]:
                try:
                    videos.append(probe(path))
                except (OSError, ValueError, KeyError, IndexError, subprocess.CalledProcessError):
                    print(f"Skipping unreadable video {display(path)}")
        formats = [(f"{label} ({len(group)})", group)
                   for label, group in (("Short", [v for v in videos if v.short]),
                                        ("Long / standard", [v for v in videos if not v.short])) if group]
        if not formats:
            parser.exit(1, "No readable videos in the selected runs.\n")
        group = choose("Select video format", formats)
        selections = [(video, *youtube.clip_text(video.path)) for video in group]
        selections = choose("Select videos", [
            (f"{title} ({video.seconds:.1f}s)\n     {video.path}", (video, title, description))
            for video, title, description in selections
        ], multiple=True)
        choices = destinations(config, [video for video, _, _ in selections])
        if not choices:
            parser.exit(1, f"No eligible destinations configured in {args.env_file}. See upload/README.md.\n")
        targets = choose("Select destinations", [(label, (label, target)) for label, target in choices], multiple=True)
        privacy = "private"
        if any(target is youtube for _, target in targets):
            privacy = choose("YouTube visibility", [(value, value) for value in ("private", "unlisted", "public")])
        print("\nReview batch")
        for label, target in targets:
            print(f"  {label}" + (f" ({privacy})" if target is youtube else ""))
        for video, title, description in selections:
            print(f"\n{display(title)}\n{display(video.path)}\n{display(description)}")
        if args.dry_run:
            print("\nDry run complete.")
            return 0
        if input("\nType UPLOAD to approve this batch and start publishing > ").strip() != "UPLOAD":
            print("Cancelled.")
            return 0
        return publish_batch(config, selections, targets, privacy)
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 0
    except (OSError, ValueError, PublishError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
