.DEFAULT_GOAL := help

PYTHON ?= python3
CLIPPER_PYTHON ?= skills/gta6-clipper/.venv/bin/python
UPLOAD_PYTHON ?= .venv/bin/python

# Match the Codex skill layout while allowing existing run locations.
GTA6_CLIPS_DIR ?= $(CURDIR)/runs
GTA6_LIVE_DIR ?= $(GTA6_CLIPS_DIR)/live
export GTA6_CLIPS_DIR GTA6_LIVE_DIR URL RUN CLIP

VOD = "$(CLIPPER_PYTHON)" skills/gta6-clipper/scripts/gta6clip.py
LIVE = "$(CLIPPER_PYTHON)" skills/gta6-live-clipper/scripts/live.py
PUBLISH = "$(UPLOAD_PYTHON)" -m upload

.PHONY: help setup setup-upload discover prep status render \
	live-start live-next live-clip live-status live-stop \
	thumbnail upload upload-preview upload-youtube upload-facebook upload-instagram

help: ## List available commands
	@awk 'BEGIN {FS = ":.*## "; print "GTA 6 Clipper\n"} /^[a-z-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nPass extra options or multiple paths with ARGS. Run make <target> ARGS=--help for CLI options.\n'

setup: ## Install the shared macOS clipper dependencies
	bash skills/gta6-clipper/scripts/setup.sh

setup-upload: ## Create the publishing environment and install its dependencies
	"$(PYTHON)" -m venv .venv
	.venv/bin/python -m pip install -r upload/requirements.txt

discover: ## Find streams to clip
	$(VOD) discover $(ARGS)

prep: ## Prepare a finished stream (URL="https://…")
	$(VOD) prep $(if $(URL),"$$URL") $(ARGS)

status: ## Show VOD processing and clip-pick status (RUN="runs/…")
	$(VOD) status $(if $(RUN),"$$RUN") $(ARGS)

render: ## Render clips from saved VOD picks (RUN="runs/…")
	$(VOD) render $(if $(RUN),"$$RUN") $(ARGS)

live-start: ## Start recording a live stream (URL="https://…")
	$(LIVE) start $(if $(URL),"$$URL") $(ARGS)

live-next: ## Get the next live transcript window (RUN="runs/live/…")
	$(LIVE) next $(if $(RUN),"$$RUN") $(ARGS)

live-clip: ## Render live clips from saved picks (RUN="runs/live/…")
	$(LIVE) clip $(if $(RUN),"$$RUN") $(ARGS)

live-status: ## Show recorder status (RUN="runs/live/…")
	$(LIVE) status $(if $(RUN),"$$RUN") $(ARGS)

live-stop: ## Stop a recorder (RUN="runs/live/…")
	$(LIVE) stop $(if $(RUN),"$$RUN") $(ARGS)

thumbnail: ## Generate a JPG and approve a clip (CLIP="path/to/clip.mp4")
	$(PUBLISH).youtube.thumbnail $(if $(CLIP),"$$CLIP") $(ARGS)

upload: ## Open the upload picker and review a batch before publishing
	$(PUBLISH).tui $(ARGS)

upload-preview: ## Review a batch in the picker without publishing
	$(PUBLISH).tui --dry-run $(ARGS)

upload-youtube: ## Send approved clips directly to YouTube (CLIP="path/to/clip.mp4")
	$(PUBLISH).youtube.upload $(if $(CLIP),"$$CLIP") $(ARGS)

upload-facebook: ## Publish approved clips directly to a Facebook Page (CLIP="path/to/clip.mp4")
	$(PUBLISH).facebook.upload $(if $(CLIP),"$$CLIP") $(ARGS)

upload-instagram: ## Publish approved clips directly to Instagram Reels (CLIP="path/to/clip.mp4")
	$(PUBLISH).instagram.upload $(if $(CLIP),"$$CLIP") $(ARGS)
