// Phase 7 (R12): a stand-in for the Caddyfile's security headers (commit D,
// which only takes effect on the VM). It forwards every request to a local
// production build and adds exactly the headers deploy/oracle/Caddyfile
// sets on the site's address, so the pages can be checked for a
// Content-Security-Policy violation before deploying. A sibling of
// gzip_proxy.mjs; no compression here (Caddy's encode is unrelated).
//
//   node scripts/review/csp_proxy.mjs   (PORT=3402 TARGET=3400 by default)
import http from "http";

const PORT = Number(process.env.PORT || 3402);
const TARGET = { host: "127.0.0.1", port: Number(process.env.TARGET || 3400) };

// deploy/oracle/Caddyfile, the site's `header` block, verbatim
export const HEADERS = {
  "Strict-Transport-Security": "max-age=31536000",
  "X-Content-Type-Options": "nosniff",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
};

http.createServer((req, res) => {
  const p = http.request({ ...TARGET, path: req.url, method: req.method, headers: req.headers }, (up) => {
    res.writeHead(up.statusCode, { ...up.headers, ...HEADERS });
    up.pipe(res);
  });
  p.on("error", (e) => { res.writeHead(502); res.end(String(e)); });
  req.pipe(p);
}).listen(PORT, () => console.log(`csp proxy on :${PORT} -> :${TARGET.port}`));
