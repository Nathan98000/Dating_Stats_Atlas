# Contact sheets of every ranked city's photograph as the site crops it: the home card
# (16:10, object-position 50% 35%, with the rank medallion drawn where it sits) and the
# city-page band (16:7, same position). Also a table of each file's size and pixels.
#   python3 photo_sheets.py -> photos/sheet-NN.png, photos/photo_files.json
import json, os, urllib.request
from PIL import Image, ImageDraw, ImageFont
# Paths relative to atlas/web (Phase 6 port). The rank order comes from RANK_JSON if set,
# else from the API's default search (API, default http://127.0.0.1:8000).
WEB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PUB = os.path.join(WEB, "public", "cities")
imgs = json.load(open(os.path.join(WEB, "src", "data", "city-images.json")))
if os.environ.get("RANK_JSON"):
    rank = json.load(open(os.environ["RANK_JSON"]))
else:
    _q = {"seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]}, "self": {"age": 30}}
    _r = urllib.request.Request(os.environ.get("API", "http://127.0.0.1:8000") + "/v1/rank", data=json.dumps(_q).encode(), headers={"content-type": "application/json"})
    rank = json.load(urllib.request.urlopen(_r))
cities = [(i + 1, r["display_name"], r["slug"]) for i, r in enumerate(rank["ranked"])]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()
small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()

def crop(im, aspect, w, posy=0.35, posx=0.5):
    W, H = im.size
    if W / H > aspect:  # too wide: crop sides
        nw = H * aspect; x0 = (W - nw) * posx; box = (x0, 0, x0 + nw, H)
    else:
        nh = W / aspect; y0 = (H - nh) * posy; box = (0, y0, W, y0 + nh)
    return im.crop(tuple(int(round(v)) for v in box)).resize((w, int(round(w / aspect))), Image.LANCZOS)

TW = 320; CARD_H = int(TW / 1.6); BAND_H = int(TW / (16 / 7)); LABEL = 36
TILE_H = LABEL + CARD_H + 6 + BAND_H + 14
COLS, ROWS = 4, 5
files = []
for s in range(0, len(cities), COLS * ROWS):
    chunk = cities[s:s + COLS * ROWS]
    sheet = Image.new("RGB", (COLS * (TW + 16) + 16, ROWS * TILE_H + 16), (253, 247, 243))
    d = ImageDraw.Draw(sheet)
    for k, (rk, name, slug) in enumerate(chunk):
        x = 16 + (k % COLS) * (TW + 16); y = 16 + (k // COLS) * TILE_H
        meta = next((v for v in imgs.values() if v.get("file", "").startswith(slug + ".")), None)
        path = os.path.join(PUB, meta["file"]) if meta else None
        d.text((x, y), f"#{rk} {name}", fill=(32, 27, 29), font=font)
        if not path or not os.path.exists(path):
            d.text((x, y + 18), "NO PHOTO", fill=(168, 53, 42), font=small); continue
        im = Image.open(path).convert("RGB")
        kb = os.path.getsize(path) // 1024
        files.append({"rank": rk, "city": name, "file": meta["file"], "w": im.size[0], "h": im.size[1], "kb": kb, "license": meta.get("license"), "alt": meta.get("alt")})
        d.text((x, y + 18), f"{im.size[0]}x{im.size[1]}  {kb} KB  {meta.get('license','')}", fill=(117, 107, 112), font=small)
        card = crop(im, 1.6, TW)
        cd = ImageDraw.Draw(card)
        r = int(36 * TW / 249); o = int(12 * TW / 249)
        cd.ellipse((o, o, o + r, o + r), fill=(242, 181, 68))
        sheet.paste(card, (x, y + LABEL))
        band = crop(im, 16 / 7, TW)
        sheet.paste(band, (x, y + LABEL + CARD_H + 6))
    sheet.save(f"photos/sheet-{s // (COLS * ROWS) + 1:02d}.png")
json.dump(files, open("photos/photo_files.json", "w"), indent=1)
kbs = sorted(f["kb"] for f in files)
print(len(files), "photos; median KB", kbs[len(kbs)//2], "max", kbs[-1], "sum MB", sum(kbs)//1024)
print("narrowest", sorted(files, key=lambda f: f["w"])[:5])
