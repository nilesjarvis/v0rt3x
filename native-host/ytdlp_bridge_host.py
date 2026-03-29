#!/usr/bin/env python3
import json
import os
import platform
import re
import struct
import subprocess
import sys
import traceback


DOWNLOAD_DIR = "/home/user/Downloads"
COOKIE_SOURCE = os.environ.get("YTDLP_FIREFOX_COOKIE_SOURCE", "firefox")
YT_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")
PROGRESS_REGEX = re.compile(r"\[download\]\s+([0-9]+(?:\.[0-9]+)?)%")
MAX_DETAIL_LINES = 20


def send_message(message):
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("I", raw_length)[0]
    message_data = sys.stdin.buffer.read(message_length)
    if not message_data:
        return None
    return json.loads(message_data.decode("utf-8"))


def classify_failure(last_lines, return_code):
    detail_blob = "\n".join(last_lines).lower()

    if "cookies" in detail_blob and "firefox" in detail_blob:
        return (
            "Could not read Firefox cookies",
            "Close Firefox and retry, or test yt-dlp manually with --cookies-from-browser firefox",
        )

    if "permission denied" in detail_blob:
        return (
            "Permission denied while downloading",
            f"Ensure write permission for {DOWNLOAD_DIR}",
        )

    if "unable to download api page" in detail_blob or "http error 429" in detail_blob:
        return (
            "YouTube request failed or was rate-limited",
            "Retry later or update yt-dlp to the latest version",
        )

    if "unsupported url" in detail_blob:
        return (
            "yt-dlp reported an unsupported URL",
            "Confirm the selected page is a standard YouTube video URL",
        )

    return (
        f"yt-dlp exited with status {return_code}",
        "Check the last output lines for the exact reason",
    )


def has_cookie_error(last_lines):
    detail_blob = "\n".join(last_lines).lower()
    return "cookies" in detail_blob and "firefox" in detail_blob


def send_error(error, code, hint=None, details=None, watch_id=None):
    payload = {
        "type": "error",
        "error": error,
        "code": code,
        "diagnostics": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "cwd": DOWNLOAD_DIR,
            "path": os.environ.get("PATH", ""),
        },
    }

    if watch_id is not None:
        payload["watchId"] = watch_id
    if hint:
        payload["hint"] = hint
    if details:
        payload["details"] = details[-MAX_DETAIL_LINES:]

    send_message(payload)


def run_process(command):
    process = subprocess.Popen(
        command,
        cwd=DOWNLOAD_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    last_lines = []
    stdout = process.stdout
    if stdout is None:
        raise RuntimeError("Failed to capture yt-dlp output")

    for line in stdout:
        line = line.strip()
        if not line:
            continue

        last_lines.append(line)
        if len(last_lines) > MAX_DETAIL_LINES:
            last_lines.pop(0)

        progress_match = PROGRESS_REGEX.search(line)
        if progress_match:
            send_message({"type": "progress", "percent": float(progress_match.group(1))})

    return process.wait(), last_lines


def run_download(watch_id):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    video_url = f"https://www.youtube.com/watch?v={watch_id}"

    command = [
        "yt-dlp",
        "--cookies-from-browser",
        COOKIE_SOURCE,
        "--no-playlist",
        "--newline",
        video_url,
    ]

    send_message({"type": "started", "watchId": watch_id})

    try:
        return_code, last_lines = run_process(command)
    except FileNotFoundError:
        send_error(
            "yt-dlp command not found",
            "YTDLP_NOT_FOUND",
            "Install yt-dlp and ensure Firefox/native-host PATH can find it",
            watch_id=watch_id,
        )
        return
    except PermissionError:
        send_error(
            "Permission denied while launching yt-dlp",
            "YTDLP_PERMISSION",
            "Ensure yt-dlp binary is executable and allowed by system policy",
            watch_id=watch_id,
        )
        return
    except OSError as exc:
        send_error(
            f"Failed to start yt-dlp: {exc}",
            "YTDLP_LAUNCH_ERROR",
            "Check SELinux/AppArmor policy and binary location",
            watch_id=watch_id,
        )
        return

    if return_code != 0 and has_cookie_error(last_lines):
        send_message(
            {
                "type": "warning",
                "code": "COOKIE_READ_FAILED",
                "warning": "Could not read Firefox cookies. Retrying without cookies.",
            }
        )
        fallback_command = ["yt-dlp", "--no-playlist", "--newline", video_url]
        return_code, last_lines = run_process(fallback_command)

    if return_code == 0:
        send_message({"type": "done", "watchId": watch_id})
    else:
        error, hint = classify_failure(last_lines, return_code)
        send_error(error, "YTDLP_NON_ZERO", hint, last_lines, watch_id)


def main():
    while True:
        try:
            message = read_message()
            if message is None:
                break

            if message.get("type") != "download":
                send_error(
                    "Unsupported message type",
                    "BAD_MESSAGE_TYPE",
                    "The extension and native host may be out of sync",
                )
                continue

            watch_id = message.get("watchId")
            if not isinstance(watch_id, str) or not YT_ID_REGEX.match(watch_id):
                send_error(
                    "Invalid YouTube watch ID",
                    "INVALID_WATCH_ID",
                    "Use a standard YouTube watch URL with a valid video id",
                )
                continue

            run_download(watch_id)
        except Exception as exc:
            send_error(
                f"Unhandled native host error: {exc}",
                "HOST_EXCEPTION",
                "See details and diagnostics for deeper debugging",
                [traceback.format_exc(limit=8)],
            )


if __name__ == "__main__":
    main()
