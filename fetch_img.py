"""Fetch generated images listed in imgs.json and the Agmatch benefits page text."""
import io
import json
import re

import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
for item in json.load(open("imgs.json")):
    im = Image.open(io.BytesIO(requests.get(item["url"], timeout=60).content)).convert("RGB")
    im.save(f"media/{item['out']}.jpg", quality=90)
    print("ok", item["out"], im.size, flush=True)
html = requests.get("https://www.agmatch.com/benefits/", headers=UA, timeout=30).text
html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
text = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", "\n", html))
open("media/agmatch_benefits.txt", "w").write(text)
