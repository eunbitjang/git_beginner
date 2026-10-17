"""Download the hero video and recent @thearenanz social videos, encode them small for the web mockup."""
import json
import os
import subprocess
import time
import traceback

import requests

OUT = "media"
HERO_URL = "https://d8j0ntlcm91z4.cloudfront.net/user_3DK79H6kUOp5UG43YlJqRAY4u5E/hf_20261017_045025_8858a792-2051-4d7a-9af9-f4c789126896.mp4"
IG_USER = "thearenanz"
YT_CHANNEL = "https://www.youtube.com/channel/UCnVNc6b_YIAAujKiXdRt5zA"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

os.makedirs(OUT, exist_ok=True)
manifest = {"hero": None, "instagram": [], "youtube": [], "log": []}


def log(msg):
    print(msg, flush=True)
    manifest["log"].append(msg)


def download(url, path, headers=None):
    with requests.get(url, headers=headers or {"User-Agent": UA}, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


def encode(src, dst, scale, crf, max_secs=None, start=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if max_secs:
        cmd += ["-t", str(max_secs)]
    cmd += ["-vf", scale, "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    return os.path.getsize(dst)


def poster(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", src, "-frames:v", "1",
                    "-vf", "scale=720:-2", "-q:v", "4", dst], check=True)


# Hero
if os.path.exists(f"{OUT}/hero.mp4"):
    manifest["hero"] = {"file": "hero.mp4", "poster": "hero.jpg"}
else:
  try:
    download(HERO_URL, "/tmp/hero_src.mp4")
    size = encode("/tmp/hero_src.mp4", f"{OUT}/hero.mp4", "scale=1920:-2", 26)
    poster("/tmp/hero_src.mp4", f"{OUT}/hero.jpg")
    manifest["hero"] = {"file": "hero.mp4", "poster": "hero.jpg", "bytes": size}
    log(f"hero ok {size} bytes")
  except Exception:
    log("hero failed: " + traceback.format_exc(limit=1))

# Instagram (public web profile endpoint; often blocked for datacenter IPs)
try:
    r = None
    for host, ua in (("i.instagram.com", "Instagram 309.0.0.40.113 Android (31/12; 420dpi; 1080x2205; samsung; SM-G991B; o1s; exynos2100; en_US; 541635890)"),
                     ("www.instagram.com", UA)):
        for attempt in range(3):
            r = requests.get(f"https://{host}/api/v1/users/web_profile_info/?username={IG_USER}",
                             headers={"User-Agent": ua, "x-ig-app-id": "936619743392459", "Accept": "*/*"}, timeout=30)
            log(f"instagram {host} attempt {attempt} status {r.status_code}")
            if r.status_code == 200:
                break
            time.sleep(20)
        if r.status_code == 200:
            break
    r.raise_for_status()
    edges = r.json()["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
    n = 0
    for e in edges:
        node = e["node"]
        if not node.get("is_video") or not node.get("video_url"):
            continue
        n += 1
        if n > 10:
            break
        code = node["shortcode"]
        raw = f"/tmp/ig_{code}.mp4"
        try:
            download(node["video_url"], raw)
            size = encode(raw, f"{OUT}/ig_{code}.mp4", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", 28, max_secs=15)
            poster(raw, f"{OUT}/ig_{code}.jpg")
            caps = node.get("edge_media_to_caption", {}).get("edges", [])
            manifest["instagram"].append({
                "file": f"ig_{code}.mp4", "poster": f"ig_{code}.jpg", "bytes": size,
                "url": f"https://www.instagram.com/p/{code}/",
                "caption": caps[0]["node"]["text"][:200] if caps else "",
                "views": node.get("video_view_count"), "likes": node.get("edge_liked_by", {}).get("count"),
                "taken_at": node.get("taken_at_timestamp"),
            })
            log(f"ig {code} ok {size}")
        except Exception:
            log(f"ig {code} failed: " + traceback.format_exc(limit=1))
except Exception:
    log("instagram failed: " + traceback.format_exc(limit=1))

# YouTube (videos + shorts)
for tab, limit in (("shorts", 8), ("videos", 4)):
    try:
        out = subprocess.run(["yt-dlp", "--flat-playlist", "-J", "--playlist-end", str(limit), f"{YT_CHANNEL}/{tab}"],
                             capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            log(f"youtube {tab} list failed: {out.stderr[-300:]}")
            continue
        entries = json.loads(out.stdout).get("entries") or []
        log(f"youtube {tab}: {len(entries)} entries")
        for ent in entries:
            vid = ent["id"]
            raw = f"/tmp/yt_{vid}.mp4"
            entry = {"id": vid, "kind": tab, "url": f"https://www.youtube.com/watch?v={vid}",
                     "title": ent.get("title"), "views": ent.get("view_count"), "duration": ent.get("duration")}
            for name in ("maxresdefault", "hq720", "oardefault", "hqdefault"):
                tr = requests.get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", headers={"User-Agent": UA}, timeout=30)
                if tr.status_code == 200 and len(tr.content) > 5000:
                    open(f"{OUT}/ytthumb_{vid}.jpg", "wb").write(tr.content)
                    entry["thumb"] = f"ytthumb_{vid}.jpg"
                    break
            manifest.setdefault("youtube_meta", []).append(entry)
            ok = False
            for client in ("tv_simply", "tv", "mweb", "web_safari", "ios", "android_vr"):
                dl = subprocess.run(["yt-dlp", "--extractor-args", f"youtube:player_client={client}",
                                     "-f", "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b", "--remux-video", "mp4",
                                     "-o", raw, f"https://www.youtube.com/watch?v={vid}"],
                                    capture_output=True, text=True, timeout=300)
                if dl.returncode == 0 and os.path.exists(raw):
                    log(f"yt {vid} downloaded via {client}")
                    ok = True
                    break
                log(f"yt {vid} client {client} failed: {dl.stderr.strip().splitlines()[-1][:160] if dl.stderr.strip() else ''}")
            if not ok:
                continue
            if tab == "shorts":
                scale, secs, start = "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", 15, None
            else:
                scale, secs, start = "scale=1280:-2", 20, 5
            size = encode(raw, f"{OUT}/yt_{vid}.mp4", scale, 28, max_secs=secs, start=start)
            poster(raw, f"{OUT}/yt_{vid}.jpg")
            manifest["youtube"].append({"file": f"yt_{vid}.mp4", "poster": f"yt_{vid}.jpg", "bytes": size, "kind": tab,
                                        "url": f"https://www.youtube.com/watch?v={vid}", "title": ent.get("title"),
                                        "views": ent.get("view_count")})
            log(f"yt {vid} ok {size}")
    except Exception:
        log(f"youtube {tab} failed: " + traceback.format_exc(limit=1))

with open(f"{OUT}/manifest.json", "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(json.dumps(manifest, indent=2, ensure_ascii=False))
