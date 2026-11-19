"""Publish an approved MP4 and its JPG to a Facebook Page."""
from requests_toolbelt.multipart.encoder import MultipartEncoder

from ..meta import PublishError, cli, publish_receipt, request, settings
from ..youtube.upload import approved_media, save_receipt

ENV_KEYS = ("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN")


def publish(config, clip, title, description):
    account, token, version = settings(config, ENV_KEYS)
    thumbnail, approval = approved_media(clip)
    with publish_receipt(clip, "facebook", account, approval["clip_sha256"]) as (path, receipt):
        if not receipt.get("id"):
            with clip.open("rb") as video, thumbnail.open("rb") as image:
                body = MultipartEncoder(fields={
                    "source": (clip.name, video, "video/mp4"),
                    "thumb": (thumbnail.name, image, "image/jpeg"),
                    "title": title,
                    "description": description,
                    "published": "true",
                })
                save_receipt(path, receipt)
                result = request(
                    "POST", f"https://graph-video.facebook.com/{version}/{account}/videos",
                    f"Bearer {token}", data=body, headers={"Content-Type": body.content_type},
                )
            if not result.get("id"):
                raise PublishError(f"Facebook did not return a video ID. Check your Page: {path}")
            receipt["id"] = result["id"]
            save_receipt(path, receipt)
        return f"https://www.facebook.com/watch/?v={receipt['id']}"


if __name__ == "__main__":
    cli("Facebook", publish)
