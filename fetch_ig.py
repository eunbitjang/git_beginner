"""Download the Instagram reels listed in ig_list.json and encode short muted web loops."""
import json
import os
import subprocess

import requests

OUT = "media"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
os.makedirs(OUT, exist_ok=True)
result = []
for item in json.load(open("ig_list.json")):
    code = item["code"]
    raw = f"/tmp/ig_{code}.mp4"
    try:
        with requests.get(item["videoUrl"], headers={"User-Agent": UA}, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(raw, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-t", "12",
                        "-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "30", "-pix_fmt", "yuv420p", "-an",
                        "-movflags", "+faststart", f"{OUT}/ig_{code}.mp4"], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", raw, "-frames:v", "1",
                        "-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", "-q:v", "5",
                        f"{OUT}/ig_{code}.jpg"], check=True)
        entry = {k: v for k, v in item.items() if k != "videoUrl"}
        entry.update(file=f"ig_{code}.mp4", poster=f"ig_{code}.jpg", bytes=os.path.getsize(f"{OUT}/ig_{code}.mp4"))
        result.append(entry)
        print("ok", code, entry["bytes"], flush=True)
    except Exception as e:
        print("failed", code, e, flush=True)
json.dump(result, open(f"{OUT}/ig_manifest.json", "w"), indent=1, ensure_ascii=False)
