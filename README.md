# Firefox YouTube yt-dlp Bridge

This project adds a Firefox extension button that, when clicked on a YouTube video page, runs:

`yt-dlp --cookies-from-browser firefox "https://www.youtube.com/watch?v=<watch-id>"`

The command is run from `/home/user/Downloads` through a native messaging host.

## What is included

- `extension/` Firefox extension (button click + progress display)
- `native-host/ytdlp_bridge_host.py` Native messaging host that executes `yt-dlp`
- `install_native_host.sh` Installer for native host registration

## Prerequisites

- Firefox installed
- `yt-dlp` installed and available on `PATH`
- Python 3 installed

## Install

1. Register the native host:

   ```bash
   chmod +x /home/user/Documents/v0rt3x/install_native_host.sh
   /home/user/Documents/v0rt3x/install_native_host.sh
   ```

2. Load extension in Firefox:

   - Open `about:debugging#/runtime/this-firefox`
   - Click **Load Temporary Add-on...**
   - Select `/home/user/Documents/v0rt3x/extension/manifest.json`

## Usage

1. Open any YouTube watch page.
2. Start a download in one of two ways:
   - Click the extension toolbar button.
   - Right-click on YouTube video links/pages and choose **Download video with yt-dlp**.
3. Progress appears on the button badge (for example `32%`).
4. Success or errors are shown on the badge (`OK` / `ERR`) and in the button tooltip.

## Notes

- The host creates `/home/user/Downloads` if it does not exist.
- If native messaging fails, reinstall by rerunning `install_native_host.sh`.
- Error tooltips now include an error code, hint, and final yt-dlp output line for debugging.
- For full diagnostics payloads, check Firefox extension background logs in `about:debugging`.
