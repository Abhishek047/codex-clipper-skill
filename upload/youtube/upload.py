"""Upload explicitly approved clips to the OAuth account's YouTube channel."""
import argparse
import fcntl
import json
from pathlib import Path
import time

if __package__:
    from .thumbnail import approval_paths, digest
else:
    from thumbnail import approval_paths, digest


DEFAULT_ENV = Path(__file__).resolve().parents[2] / ".env"
ENV_KEYS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
SCOPE = "https://www.googleapis.com/auth/youtube"


def approved_media(clip):
    thumbnail, approval = approval_paths(clip)
    if clip.suffix.lower() != ".mp4" or not all(
        path.is_file() for path in (clip, thumbnail, approval)
    ):
        raise ValueError(f"Run thumbnail.py to approve this MP4 first: {clip}")
    record = json.loads(approval.read_text(encoding="utf-8"))
    if record.get("clip_sha256") != digest(clip) or record.get("thumbnail_sha256") != digest(thumbnail):
        raise ValueError(f"Clip or thumbnail changed. Review and approve again: {clip}")
    return thumbnail, record


def approved_thumbnail(clip):
    return approved_media(clip)[0]


def clip_text(clip):
    title = clip.stem.replace("_", " ")
    description = ""
    sidecar = clip.with_suffix(".txt")
    if sidecar.is_file():
        header, _, remainder = sidecar.read_text(encoding="utf-8").partition("\n")
        if header.startswith("TITLE:"):
            title = header.removeprefix("TITLE:").strip() or title
            description = remainder.strip().removeprefix("CAPTION:").strip()
        else:
            description = (header + "\n" + remainder).strip()
        description = description.split("\nCategory:", 1)[0].rstrip()
    return title, description


def metadata(clip, privacy, made_for_kids):
    return video_body(*clip_text(clip), privacy, made_for_kids)


def video_body(title, description, privacy, made_for_kids):
    return {
        "snippet": {
            "title": title.replace("<", "").replace(">", "")[:100].strip() or "GTA 6 clip",
            "description": description.replace("<", "").replace(">", "").encode()[:5000]
            .decode("utf-8", errors="ignore"),
            "categoryId": "20",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids},
    }


def youtube_client(env_file):
    from dotenv import dotenv_values
    if not env_file.is_file():
        raise ValueError(f"YouTube credentials file is missing: {env_file}")
    return client_from_config(dotenv_values(env_file, interpolate=False))


def client_from_config(config):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    keys = ENV_KEYS
    missing = [key for key in keys if not config.get(key)]
    if missing:
        raise ValueError(f"Missing YouTube OAuth values: {', '.join(missing)}")

    credentials = Credentials(
        token=None,
        client_id=config[keys[0]],
        client_secret=config[keys[1]],
        refresh_token=config[keys[2]],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[SCOPE],
    )
    return build("youtube", "v3", credentials=credentials)


def wait_for_processing(youtube, video_id):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        result = youtube.videos().list(part="processingDetails", id=video_id).execute()
        items = result.get("items", [])
        status = items[0].get("processingDetails", {}).get("processingStatus") if items else None
        if status == "succeeded":
            return
        if status in {"failed", "terminated"}:
            raise ValueError(f"YouTube processing {status} for {video_id}")
        time.sleep(5)
    raise ValueError(f"YouTube is still processing {video_id}. Rerun to resume the thumbnail step.")


def save_receipt(path, receipt):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def upload(youtube, clip, body):
    from googleapiclient.http import MediaFileUpload

    receipt_path = clip.with_suffix(".youtube.json")
    with clip.with_suffix(".youtube.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        thumbnail = approved_thumbnail(clip)
        clip_hash = digest(clip)
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt["clip_sha256"] != clip_hash:
                raise ValueError(f"The upload receipt belongs to a different version: {receipt_path}")
            if not receipt.get("video_id"):
                raise ValueError(f"Previous upload outcome is unknown. Check YouTube Studio: {receipt_path}")
        else:
            receipt = {"clip_sha256": clip_hash}
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(str(clip), mimetype="video/mp4", resumable=True),
                notifySubscribers=False,
            )
            save_receipt(receipt_path, receipt)
            result = None
            while result is None:
                _, result = request.next_chunk(num_retries=3)
            receipt["video_id"] = result["id"]
            save_receipt(receipt_path, receipt)

        video_id = receipt["video_id"]
        print(f"YouTube video: https://youtu.be/{video_id}", flush=True)
        thumbnail_hash = digest(thumbnail)
        if receipt.get("thumbnail_sha256") != thumbnail_hash:
            wait_for_processing(youtube, video_id)
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg"),
            ).execute(num_retries=3)
            receipt["thumbnail_sha256"] = thumbnail_hash
            save_receipt(receipt_path, receipt)
        print(f"Thumbnail set for {video_id}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", nargs="+", type=Path)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    parser.add_argument("--made-for-kids", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Check approval and preview metadata locally")
    args = parser.parse_args()

    try:
        clips = {}
        for path in args.clips:
            clip = path.resolve()
            approved_thumbnail(clip)
            clips[clip] = metadata(clip, args.privacy, args.made_for_kids)
        if args.dry_run:
            for clip, body in clips.items():
                print(f"{clip}\n{json.dumps(body, indent=2, ensure_ascii=False)}")
            return
        with youtube_client(args.env_file) as youtube:
            for clip, body in clips.items():
                upload(youtube, clip, body)
    except ImportError:
        parser.exit(1, "Install the dependencies from upload/youtube/requirements.txt first.\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except Exception as error:
        from google.auth.exceptions import GoogleAuthError
        from googleapiclient.errors import HttpError

        if isinstance(error, GoogleAuthError):
            parser.exit(1, "YouTube OAuth failed. Check the client credentials, refresh token, and scope.\n")
        if isinstance(error, HttpError):
            parser.exit(1, f"YouTube API error (HTTP {error.resp.status}): {error.reason}\n")
        raise


if __name__ == "__main__":
    main()
