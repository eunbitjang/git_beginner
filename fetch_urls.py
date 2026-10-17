"""Download each URL in urls.json and encode web-ready variants (desktop 4K + mobile 720p) plus a poster."""
import json
import subprocess

import requests

ENC = ["-c:v", "libx264", "-preset", "veryslow", "-tune", "film", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"]

for item in json.load(open("urls.json")):
    raw = "/tmp/src.mp4"
    with requests.get(item["url"], stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(raw, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    out = item["out"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=bit_rate,size,duration:stream=width,height,codec_name,r_frame_rate",
                            "-of", "compact", raw], capture_output=True, text=True).stdout
    open(f"media/{out}_source.txt", "w").write(probe)
    print(probe, flush=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-vf", "scale=3840:2160:flags=lanczos",
                    *ENC, "-profile:v", "high", "-level", "5.1", "-crf", "17", "-maxrate", "13M", "-bufsize", "26M",
                    f"media/{out}_4k.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-vf", "scale=1280:720:flags=lanczos",
                    *ENC, "-crf", "19", "-maxrate", "4M", "-bufsize", "8M", f"media/{out}_720.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", raw, "-frames:v", "1",
                    "-vf", "scale=1920:1080:flags=lanczos", "-q:v", "2", f"media/{out}_poster.jpg"], check=True)
    for t in (1, 3, 5, 7):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", raw, "-frames:v", "1",
                        f"media/{out}_frame{t}.png"], check=True)
    print("ok", out, flush=True)
