"""Publish an approved MP4 as a Reel on an Instagram professional account."""
import time

from ..meta import PublishError, cli, publish_receipt, request, settings
from ..youtube.upload import approved_media, save_receipt

ENV_KEYS = ("INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN")


def caption(title, description):
    return "\n\n".join(filter(None, (title, description)))[:2200]


def wait_until_ready(base, container_id, auth):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        result = request("GET", f"{base}/{container_id}", auth, params={"fields": "status_code"})
        status = result.get("status_code")
        if status == "FINISHED":
            return
        if status in {"ERROR", "EXPIRED", "PUBLISHED"}:
            raise PublishError(f"Instagram container {container_id} has status {status}")
        time.sleep(10)
    raise PublishError(f"Instagram is still processing container {container_id}; no publish was requested")


def publish(config, clip, title, description):
    account, token, version = settings(config, ENV_KEYS)
    _, approval = approved_media(clip)
    auth = f"Bearer {token}"
    base = f"https://graph.facebook.com/{version}"
    with publish_receipt(clip, "instagram", account, approval["clip_sha256"]) as (path, receipt):
        if not receipt.get("id"):
            container = request("POST", f"{base}/{account}/media", auth, data={
                "media_type": "REELS", "upload_type": "resumable", "share_to_feed": "true",
                "caption": caption(title, description),
                "thumb_offset": str(approval.get("timestamp_ms", 0)),
            })
            container_id = str(container.get("id", ""))
            if not container_id.isascii() or not container_id.isdecimal():
                raise PublishError("Instagram did not return a valid container ID")
            upload_url = f"https://rupload.facebook.com/ig-api-upload/{version}/{container_id}"
            with clip.open("rb") as video:
                upload = request("POST", upload_url, f"OAuth {token}", data=video, headers={
                    "offset": "0", "file_size": str(clip.stat().st_size),
                    "Content-Type": "application/octet-stream",
                })
            if upload.get("success") is not True:
                raise PublishError(f"Instagram rejected the video for container {container_id}")
            wait_until_ready(base, container_id, auth)
            receipt["container_id"] = container_id
            save_receipt(path, receipt)
            result = request(
                "POST", f"{base}/{account}/media_publish", auth, data={"creation_id": container_id}
            )
            if not result.get("id"):
                raise PublishError(f"Instagram did not return a media ID. Check your account: {path}")
            receipt["id"] = result["id"]
            save_receipt(path, receipt)
        media_id = receipt["id"]
    try:
        media = request("GET", f"{base}/{media_id}", auth, params={"fields": "permalink"})
    except PublishError:
        return f"Instagram Reel ID {media_id}"
    return media.get("permalink") or f"Instagram Reel ID {media_id}"


if __name__ == "__main__":
    cli("Instagram", publish)
