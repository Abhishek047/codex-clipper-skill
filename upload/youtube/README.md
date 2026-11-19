# Upload approved clips to YouTube

Use Python 3.11+ and FFmpeg. Run these commands from the repository root with
your Python environment active.

```sh
python -m pip install -r upload/youtube/requirements.txt
```

Enable YouTube Data API v3 in your Google Cloud OAuth project. Obtain a refresh
token for the channel you want to upload to with the
`https://www.googleapis.com/auth/youtube` scope. The upload uses the channel
selected during OAuth consent. Add these values to the repository root's
gitignored `.env` file, or pass another dotenv file with `--env-file`.

```dotenv
YOUTUBE_CLIENT_ID=your_oauth_client_id
YOUTUBE_CLIENT_SECRET=your_oauth_client_secret
YOUTUBE_REFRESH_TOKEN=your_channel_refresh_token
```

Watch each clip, then pass only the approved MP4 paths. The thumbnail script
saves a JPEG of the chosen frame and an approval record beside each video.
`--at` picks the frame in seconds and defaults to the start of the clip.

```sh
python upload/youtube/thumbnail.py "runs/example/clips/clip_01.mp4" --at 3
python upload/youtube/upload.py "runs/example/clips/clip_01.mp4" --dry-run
python upload/youtube/upload.py "runs/example/clips/clip_01.mp4"
```

Both commands accept multiple MP4 paths. The uploader uses the clipper's
adjacent TXT file for title and description when present. The default visibility
is private. Use `--privacy unlisted` or `--privacy public` to change it, and
`--made-for-kids` if applicable. YouTube may restrict uploads from unverified
API projects to private visibility.

The uploader prints the video URL and waits for processing before setting the
thumbnail. If that step times out or fails, rerun the command to resume using
the local `.youtube.json` receipt. If a receipt has no video ID, check YouTube
Studio before retrying. Add the matching video's ID as `video_id` if the upload
succeeded, or remove the receipt only after confirming that no video was created.
Use YouTube Studio to change privacy or metadata after the initial upload.

[YouTube OAuth documentation](https://developers.google.com/youtube/data/guides/authentication)
· [Video uploads](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
· [Custom thumbnails](https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set)
