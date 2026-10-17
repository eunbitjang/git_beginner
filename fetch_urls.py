"""Download each URL in urls.json and encode it as a muted, web-ready mp4 plus a poster frame."""
import json
import subprocess

import requests

for item in json.load(open("urls.json")):
    raw = "/tmp/src.mp4"
    with requests.get(item["url"], stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(raw, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    out = item["out"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-vf", "scale=1920:-2", "-c:v", "libx264",
                    "-preset", "slow", "-crf", "26", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
                    f"media/{out}.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", raw, "-frames:v", "1",
                    "-vf", "scale=1280:-2", "-q:v", "4", f"media/{out}.jpg"], check=True)
    print("ok", out, flush=True)
