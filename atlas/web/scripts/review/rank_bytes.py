# /api/rank for the default search (the body m1/m2 send), raw from `next start` and gzipped
# at levels 6 and 9, for comparison with commit A's Caddy encode.   python3 rank_bytes.py -> rank_bytes.json
import json, gzip, urllib.request
body = {"self": {"age": 30}, "seeking": {"sex": "male", "age": [28, 40], "marital": ["never_married", "previously_married"]}, "sort": "best_first"}
req = urllib.request.Request("http://localhost:3300/api/rank", data=json.dumps(body).encode(), headers={"content-type": "application/json", "accept-encoding": "identity"})
raw = urllib.request.urlopen(req).read()
out = {"raw": len(raw), "gzip6": len(gzip.compress(raw, 6)), "gzip9": len(gzip.compress(raw, 9))}
json.dump(out, open("rank_bytes.json", "w"), indent=1); print(out)
