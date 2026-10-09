#!/bin/bash
# What only the server shows, on the live site (still Phase 4 / m4.2.0 on 8 October 2026):
# compression of HTML, JS and /api/rank, and caching of the photographs and static files.
L=https://dating-stats-atlas.duckdns.org
echo "== nav (is Phase 5 live?)"; curl -s $L/ | grep -o -E 'Rankings|Compare cities|About the site|How it works' | sort | uniq -c
echo "== home HTML, gzip asked"; curl -s -D - -o /dev/null -H 'accept-encoding: gzip, br, zstd' $L/ | grep -i -E '^HTTP/|content-encoding|cache-control'
echo "== home HTML bytes on the wire (gzip asked)"; curl -s -o /dev/null -w '%{size_download}\n' -H 'accept-encoding: gzip, br, zstd' $L/
JS=$(curl -s $L/ | grep -o '/_next/static/chunks/[a-z0-9]*\.js' | head -1)
echo "== a JS chunk"; curl -s -D - -o /dev/null -H 'accept-encoding: gzip, br, zstd' $L$JS | grep -i -E 'content-encoding|cache-control'
echo "== /api/rank, default search, gzip asked"; curl -s -D - -o /dev/null -w 'bytes on the wire: %{size_download}\n' -H 'accept-encoding: gzip, br, zstd' -H 'content-type: application/json' -X POST $L/api/rank -d '{"self":{"age":30},"seeking":{"sex":"male","age":[28,40],"marital":["never_married","previously_married"]},"sort":"best_first"}' | grep -i -E 'content-encoding|bytes on the wire'
echo "== a city photograph"; curl -s -I $L/cities/san-francisco-california.jpg | grep -i -E '^HTTP/|cache-control|content-length|etag'
