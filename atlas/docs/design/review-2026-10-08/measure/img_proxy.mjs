// A stand-in for right-sized photographs: on :3302, answers /cities/*.jpg with a 720px-wide
// WebP at quality 72 (made once with sharp, then cached) and forwards everything else to the
// gzip stand-in on :3301. Used only by m2b to measure the recommendation's effect.
import http from "http";
import sharp from "/opt/npm-tools/node_modules/sharp/dist/index.cjs";
import { readFileSync } from "fs";
const PUB = "/home/claude/rv/repo/atlas/web/public";
const cache = new Map();
http.createServer(async (req, res) => {
  const path = req.url.split("?")[0];
  if (/^\/cities\/[a-z0-9-]+\.jpg$/.test(path)) {
    if (!cache.has(path)) cache.set(path, await sharp(readFileSync(PUB + path)).resize({ width: 720 }).webp({ quality: 72 }).toBuffer());
    const b = cache.get(path);
    res.writeHead(200, { "content-type": "image/webp", "content-length": b.length });
    return res.end(b);
  }
  const p = http.request({ host: "127.0.0.1", port: 3301, path: req.url, method: req.method, headers: req.headers }, (up) => { res.writeHead(up.statusCode, up.headers); up.pipe(res); });
  req.pipe(p);
}).listen(3302, () => console.log("image stand-in on :3302"));
