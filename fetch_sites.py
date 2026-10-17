"""Collect the image assets used on the Agmatch and Agwool sites, resized for a web mockup."""
import io
import json
import os
import re

import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
PAGES = {
    "agmatch": ["https://www.agmatch.com/", "https://www.agmatch.com/benefits/", "https://www.agmatch.com/become-a-member/"],
    "agwool": ["https://agwoolnz.com/", "https://agwoolnz.com/about-agwool/", "https://agwoolnz.com/shop/",
               "https://agwoolnz.com/shop/page/2/", "https://agwoolnz.com/news-media/"],
}
PAT = re.compile(r"https?://(?:www\.)?(?:agmatch\.com|agmatch\.co\.nz|agwoolnz\.com)/wp-content/uploads/[^\s\"'()<>]+?\.(?:jpe?g|png|webp)", re.I)
manifest = {}
for site, pages in PAGES.items():
    os.makedirs(f"media/{site}", exist_ok=True)
    urls, texts = set(), {}
    for p in pages:
        try:
            html = requests.get(p, headers=UA, timeout=30).text
            texts[p] = len(html)
            for u in PAT.findall(html):
                urls.add(re.sub(r"-\d+x\d+(?=\.\w+$)", "", u))
                urls.add(u)
        except Exception as e:
            texts[p] = str(e)
    saved = []
    for u in sorted(urls):
        name = re.sub(r"[^A-Za-z0-9._-]", "_", u.split("/uploads/")[1])
        try:
            r = requests.get(u, headers=UA, timeout=30)
            if r.status_code != 200 or len(r.content) < 3000:
                continue
            im = Image.open(io.BytesIO(r.content))
            has_alpha = im.mode in ("RGBA", "LA", "P")
            im = im.convert("RGBA" if has_alpha else "RGB")
            if im.width > 1800:
                im = im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS)
            base = os.path.splitext(name)[0]
            out = f"media/{site}/{base}.{'png' if has_alpha else 'jpg'}"
            im.save(out, **({} if has_alpha else {"quality": 86}))
            saved.append({"src": u, "file": out, "w": im.width, "h": im.height, "bytes": os.path.getsize(out)})
        except Exception as e:
            print("skip", u, e)
    manifest[site] = {"pages": texts, "images": saved}
    print(site, len(saved), "images", texts, flush=True)
json.dump(manifest, open("media/sites_manifest.json", "w"), indent=1)
