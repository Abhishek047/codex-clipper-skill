# Clip review and upload

After rendering, show a numbered list with each clip's title and clickable MP4 link so the user
can watch it. Ask which numbers they approve and where those clips should go. Offer the
terminal picker (`python -m upload.tui` from the repository root) for choosing runs, video
format, clips and destinations in one batch. For choices made in chat, offer keeping files
local and the destinations configured in `.env`: YouTube, Facebook Page, and Instagram
professional account. YouTube defaults to private. Facebook and Instagram publish directly.
The user can select multiple clips, name destinations per clip, or defer. If a platform is
unavailable, keep those files local and explain what is missing.

Treat a reply such as “1 and 3 to YouTube, keep 2 local” as approval and permission to upload
only clips 1 and 3. If a clip or destination is ambiguous, ask only about the missing choice.
Use public or unlisted visibility only when the user explicitly requests it. Never infer a
destination from the source streaming platform or treat silence as approval.

For confirmed uploads, locate `upload/` in the repository containing the resolved
skill paths, or use the matching uploader in the current project if the skills were installed
as copies. Use the gta6-clipper venv's Python. See `upload/README.md` for dependencies and
repository-root `.env` credentials. If dependencies are missing, use the project's setup
instructions to install them.
If the uploader or credentials are missing, report the blocker without exposing secret values.

For approvals given in chat, pass only the selected MP4 paths to `upload/youtube/thumbnail.py`,
then pass the approved paths to the requested platform's upload script. Use the frame timestamp
the user specifies and pass `--privacy` for YouTube when they request public or unlisted.
Report the resulting video links and any
pending thumbnail steps. For local or deferred clips, leave the MP4s available for later review.
