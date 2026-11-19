"""Shared configuration, HTTP requests, and publish receipts for Meta."""
import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re

from dotenv import dotenv_values
import requests

from .youtube.upload import DEFAULT_ENV, approved_media, clip_text, save_receipt


class PublishError(RuntimeError):
    pass


def settings(config, keys):
    missing = [key for key in keys if not config.get(key)]
    if missing:
        raise PublishError(f"Missing .env values: {', '.join(missing)}")
    account, token = (config[key] for key in keys)
    version = config.get("META_GRAPH_VERSION") or "v27.0"
    if not account.isascii() or not account.isdecimal():
        raise PublishError(f"{keys[0]} must be a numeric account ID")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+", version):
        raise PublishError("META_GRAPH_VERSION must look like v27.0")
    return account, token, version


def request(method, url, authorization, **kwargs):
    headers = {"Authorization": authorization, **kwargs.pop("headers", {})}
    try:
        response = requests.request(
            method, url, headers=headers, timeout=(15, 300), allow_redirects=False, **kwargs
        )
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise PublishError(f"Meta request failed ({type(error).__name__})") from None
    if not isinstance(payload, dict):
        raise PublishError("Meta returned an unexpected response")
    if response.status_code >= 300 or "error" in payload:
        code = payload.get("error", {}).get("code")
        detail = f", Graph code {code}" if isinstance(code, int) else ""
        raise PublishError(f"Meta request failed (HTTP {response.status_code}{detail})")
    return payload


@contextmanager
def publish_receipt(clip, platform, account, clip_hash):
    path = clip.with_suffix(f".{platform}-{account}.json")
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = {"clip_sha256": clip_hash}
        if path.exists():
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if receipt.get("clip_sha256") != clip_hash:
                raise PublishError(f"Receipt belongs to a different clip version: {path}")
            if not receipt.get("id"):
                raise PublishError(f"Previous publish outcome is unknown. Check your account: {path}")
        yield path, receipt


def cli(platform, publisher):
    parser = argparse.ArgumentParser(description=f"Publish approved MP4s to {platform}")
    parser.add_argument("clips", type=Path, nargs="+")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    try:
        config = dotenv_values(args.env_file, interpolate=False)
        clips = [path.resolve() for path in args.clips]
        for clip in clips:
            approved_media(clip)
        for clip in clips:
            title, description = clip_text(clip)
            print(publisher(config, clip, title, description))
    except (PublishError, OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
