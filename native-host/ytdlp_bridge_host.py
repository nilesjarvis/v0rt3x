#!/usr/bin/env python3
import json
import os
import re
import struct
import subprocess
import sys


DOWNLOAD_DIR = "/home/user/Downloads"
YT_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")
PROGRESS_REGEX = re.compile(r"\[download\]\s+([0-9]+(?:\.[0-9]+)?)%")


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


def run_download(watch_id):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    video_url = f"https://www.youtube.com/watch?v={watch_id}"

    command = [
        "yt-dlp",
        "--cookies-from-browser",
        "firefox",
        "--newline",
        video_url,
    ]

    send_message({"type": "started", "watchId": watch_id})

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
        if len(last_lines) > 10:
            last_lines.pop(0)

        progress_match = PROGRESS_REGEX.search(line)
        if progress_match:
            send_message({"type": "progress", "percent": float(progress_match.group(1))})

    return_code = process.wait()

    if return_code == 0:
        send_message({"type": "done", "watchId": watch_id})
    else:
        send_message(
            {
                "type": "error",
                "watchId": watch_id,
                "error": "yt-dlp exited with non-zero status",
                "details": last_lines,
            }
        )


def main():
    while True:
        try:
            message = read_message()
            if message is None:
                break

            if message.get("type") != "download":
                send_message({"type": "error", "error": "Unsupported message type"})
                continue

            watch_id = message.get("watchId")
            if not isinstance(watch_id, str) or not YT_ID_REGEX.match(watch_id):
                send_message({"type": "error", "error": "Invalid YouTube watch ID"})
                continue

            run_download(watch_id)
        except Exception as exc:
            send_message({"type": "error", "error": str(exc)})


if __name__ == "__main__":
    main()
