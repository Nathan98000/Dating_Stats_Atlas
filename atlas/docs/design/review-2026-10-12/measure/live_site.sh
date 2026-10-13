#!/bin/bash
# Round 4 (12 October 2026): what only the server shows, on the live site. Round 3's checks
# (compression, caching), plus the old addresses' redirects, the certificates, the security
# headers, crawl rules, sitemap, icons and canonical links. One request each; no load.
#   bash live_site.sh > live_site.txt
L=https://datingscenedata.com
H='accept-encoding: gzip, br, zstd'
hdr() { grep -i -E "$1"; }
echo "== home HTML, gzip asked"; curl -s -D - -o /dev/null -H "$H" $L/ | hdr '^HTTP/|content-encoding|cache-control|strict-transport|content-security|x-content-type|referrer-policy|permissions-policy|x-frame|server|alt-svc'
echo "== home HTML bytes on the wire (gzip asked) / raw"; curl -s -o /dev/null -w '%{size_download}\n' -H "$H" $L/; curl -s -o /dev/null -w '%{size_download}\n' $L/
JS=$(curl -s $L/ | grep -o '/_next/static/chunks/[a-z0-9]*\.js' | head -1)
echo "== a JS chunk ($JS)"; curl -s -D - -o /dev/null -H "$H" $L$JS | hdr 'content-encoding|cache-control'
CSS=$(curl -s $L/ | grep -o '/_next/static/[a-z0-9/]*\.css' | head -1)
echo "== the CSS ($CSS)"; curl -s -D - -o /dev/null -H "$H" $L$CSS | hdr 'content-encoding|cache-control'
FONT=$(curl -s $L/ | grep -o '/_next/static/media/[A-Za-z0-9_.-]*\.woff2' | head -1)
echo "== a font ($FONT)"; curl -s -D - -o /dev/null $L$FONT | hdr 'cache-control|content-length'
echo "== /api/rank, default search, gzip asked"; curl -s -D - -o /dev/null -w 'bytes on the wire: %{size_download}\n' -H "$H" -H 'content-type: application/json' -X POST $L/api/rank -d '{"self":{"age":30},"seeking":{"sex":"male","age":[28,40],"marital":["never_married","previously_married"]},"sort":"best_first"}' | hdr 'content-encoding|cache-control|bytes on the wire'
echo "== /api/rank with the visitor's sex (must refuse)"; curl -s -o /dev/null -w '%{http_code}\n' -H 'content-type: application/json' -X POST $L/api/rank -d '{"self":{"age":30,"sex":"female"},"seeking":{"sex":"male","age":[28,40],"marital":["never_married"]}}'
echo "== a card photograph (WebP copy)"; curl -s -I $L/cities/w/san-francisco-california-720.webp | hdr '^HTTP/|cache-control|content-length|content-type|etag'
echo "== an original photograph"; curl -s -I $L/cities/san-francisco-california.jpg | hdr '^HTTP/|cache-control|content-length'
echo "== a link preview"; curl -s -I $L/cities/og/austin-texas.jpg | hdr '^HTTP/|cache-control|content-length|content-type'
echo "== home preview"; curl -s -I $L/og/home.png | hdr '^HTTP/|cache-control|content-length|content-type'
echo "== a map"; curl -s -I -H "$H" $L/map/12420.svg | hdr '^HTTP/|cache-control|content-length|content-encoding|content-type'
echo "== favicon.ico / icon / apple-touch-icon / manifest"
for p in /favicon.ico /icon.png /icon.svg /apple-touch-icon.png /apple-icon.png /manifest.webmanifest /site.webmanifest; do printf '%s ' $p; curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}\n' $L$p; done
echo "== icons the home page links"; curl -s $L/ | grep -o -E '<link[^>]*rel="(icon|apple-touch-icon|shortcut icon|manifest)"[^>]*>'
echo "== robots.txt"; curl -s -w '\n[%{http_code}]\n' $L/robots.txt | head -20
echo "== sitemap.xml"; curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $L/sitemap.xml
echo "== canonical links"; for p in / /city/austin-texas "/city/austin-texas?self_age=30&sex=male&age=28-40" /compare/austin-texas/denver-colorado /about /stats/rent_1br; do printf '%s -> ' "$p"; curl -s "$L$p" | grep -o '<link rel="canonical"[^>]*>' || echo none; done
echo "== starter files left in public/ (Next's defaults)"; for p in /next.svg /vercel.svg /file.svg /globe.svg /window.svg; do printf '%s ' $p; curl -s -o /dev/null -w '%{http_code}\n' $L$p; done
echo "== the old addresses (path and query kept?)"
for o in https://dating-stats-atlas.duckdns.org https://datingscenedata.duckdns.org https://www.datingscenedata.com http://datingscenedata.com; do
  printf '%s -> ' "$o/city/austin-texas?x=1"; curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "$o/city/austin-texas?x=1"; done
echo "== certificates"
for h in datingscenedata.com www.datingscenedata.com datingscenedata.duckdns.org dating-stats-atlas.duckdns.org; do
  printf '%s: ' $h; echo | openssl s_client -servername $h -connect $h:443 2>/dev/null | openssl x509 -noout -subject -issuer -enddate -ext subjectAltName 2>/dev/null | tr '\n' ' '; echo; done
echo "== TLS versions"; for v in tls1_1 tls1_2 tls1_3; do printf '%s ' $v; echo | openssl s_client -$v -connect datingscenedata.com:443 -servername datingscenedata.com 2>&1 | grep -q 'Cipher is (NONE)\|alert\|wrong version\|no protocols' && echo refused || echo accepted; done
echo "== 404 status"; curl -s -o /dev/null -w '%{http_code}\n' $L/no-such-page
echo "== internal API not exposed"; for p in /v1/health /v1/meta; do printf '%s ' $p; curl -s -o /dev/null -w '%{http_code}\n' $L$p; done
