"""Generate a thumbnail and record approval for the selected MP4."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def approval_paths(clip):
    return clip.with_suffix(".thumbnail.jpg"), clip.with_suffix(".approval.json")


def generate(clip, timestamp):
    if clip.suffix.lower() != ".mp4" or not clip.is_file():
        raise ValueError(f"Choose an existing MP4: {clip}")
    if not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError("Thumbnail timestamp must be a finite, nonnegative number")
    thumbnail, approval = approval_paths(clip)
    clip_hash = digest(clip)
    with TemporaryDirectory(dir=clip.parent) as folder:
        frame = Path(folder) / "frame.jpg"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(timestamp),
             "-i", str(clip), "-map", "0:v:0", "-frames:v", "1",
             "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,setsar=1",
             "-pix_fmt", "yuvj420p", "-q:v", "3", str(frame)],
            check=True,
        )
        if not frame.is_file() or not frame.stat().st_size:
            raise ValueError(f"No thumbnail frame at {timestamp:g} seconds: {clip}")
        if digest(clip) != clip_hash:
            raise ValueError(f"Clip changed during thumbnail generation: {clip}")
        record = Path(folder) / "approval.json"
        record.write_text(json.dumps({
            "clip_sha256": clip_hash,
            "timestamp_ms": round(timestamp * 1000),
            "thumbnail_sha256": digest(frame),
        }) + "\n", encoding="utf-8")
        frame.replace(thumbnail)
        record.replace(approval)
    return thumbnail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", nargs="+", type=Path)
    parser.add_argument("--at", type=float, default=0, help="Frame timestamp in seconds")
    args = parser.parse_args()
    try:
        for clip in args.clips:
            print(generate(clip.resolve(), args.at))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
