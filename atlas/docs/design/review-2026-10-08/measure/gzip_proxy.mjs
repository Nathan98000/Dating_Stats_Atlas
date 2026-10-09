// A stand-in for Caddy's `encode zstd gzip` (Phase 5 commit A, which only takes effect on
// the VM): forwards to the local production build and gzips any response that arrives
// uncompressed (here: /api/rank, which `next start` sends raw). Used only to measure what
// the phone sees once A is deployed.   node gzip_proxy.mjs  -> :3301 -> :3300
import http from "http";
import zlib from "zlib";
const TARGET = { host: "127.0.0.1", port: 3300 };
http.createServer((req, res) => {
  const p = http.request({ ...TARGET, path: req.url, method: req.method, headers: req.headers }, (up) => {
    const headers = { ...up.headers };
    const accepts = /gzip/.test(req.headers["accept-encoding"] || "");
    const type = headers["content-type"] || "";
    if (accepts && !headers["content-encoding"] && /json|text|javascript/.test(type)) {
      delete headers["content-length"];
      headers["content-encoding"] = "gzip";
      headers["vary"] = "Accept-Encoding";
      res.writeHead(up.statusCode, headers);
      up.pipe(zlib.createGzip({ level: 5 })).pipe(res);
    } else {
      res.writeHead(up.statusCode, headers);
      up.pipe(res);
    }
  });
  req.pipe(p);
}).listen(3301, () => console.log("gzip proxy on :3301"));
