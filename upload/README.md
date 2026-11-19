# Publish clips from the terminal

From the repository root, use Python 3.10+ with FFmpeg and FFprobe on your PATH.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r upload/requirements.txt
.venv/bin/python -m upload.tui
```

Select one or more runs, Short or Long / standard, one or more videos, then
one or more destinations. Enter comma-separated numbers or `all` in multi-select
menus. Use `q` to exit a menu. The review shows the paths, titles, captions,
destinations and YouTube visibility. Type `UPLOAD` to approve the whole batch.
Use `--dry-run` to preview without generating thumbnails or calling any APIs.

The picker searches `runs/`, the default clipper run directory, and paths
configured in your shell via `GTA6_CLIPS_DIR` and `GTA6_LIVE_DIR`. Pass
`--runs-dir /path/to/runs` (repeatable) to override the search roots. Only MP4s
in finished `clips` folders appear. Short means square or vertical and at
most 180 seconds. Other videos appear under Long / standard. This filter
uses the existing files and leaves encoding and classification to the platform.

## Configure destinations

Put credentials in the gitignored repository-root `.env` or use `--env-file`.
Set only the groups you want. The picker checks which groups are configured
locally. The platforms validate permissions and tokens when you publish.

```dotenv
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=

INSTAGRAM_USER_ID=
INSTAGRAM_ACCESS_TOKEN=

# Optional
META_GRAPH_VERSION=v27.0
```

- **YouTube** uses the channel selected during OAuth consent, defaults to private,
  and uploads the generated JPG after processing. See the [OAuth setup](youtube/README.md).
- **Facebook** publishes to a Page via Page Videos, with the title, caption,
  and generated JPG. Use a Page token with `pages_manage_posts`,
  `pages_read_engagement`, and `pages_show_list`, authorized by a user with
  the Page's Create Content task. [Meta Page Videos reference](https://developers.facebook.com/docs/graph-api/reference/page/videos/)
- **Instagram** publishes Reels to a professional account linked to a Facebook
  Page. With Facebook Login for Business, use the connected Page access token
  and the Instagram professional account's numeric ID. The token needs
  `instagram_basic`, `instagram_content_publish`, and `pages_read_engagement`.
  Instagram appears for short selections of at least three seconds. It generates
  the Reel cover from the same video timestamp used for the local JPG. The title
  goes on the first line of the Instagram caption, followed by the description
  and hashtags, up to 2,200 characters. [Meta publishing guide](https://developers.facebook.com/documentation/instagram-platform/content-publishing)

The picker reads title and description from the clip's adjacent TXT, when
present. A batch uses the same selected destinations for every clip. Run the
picker again to send a different set of clips to other destinations.

## Publish approved clips without the picker

```sh
.venv/bin/python upload/youtube/thumbnail.py "runs/example/clips/clip_01.mp4" --at 1
.venv/bin/python -m upload.facebook.upload "runs/example/clips/clip_01.mp4"
.venv/bin/python -m upload.instagram.upload "runs/example/clips/clip_01.mp4"
```

A successful publish writes a receipt beside the clip. Keep receipts to avoid
duplicate posts if you rerun the batch. If a Meta receipt has no `id`, check
the Page or Instagram account before retrying. Record the matching media ID in
that receipt if the post exists. Remove an incomplete receipt only after
confirming the platform created no post.
