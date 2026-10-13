// Round 4 (12 October 2026): a Node port of round 3's cold_read_driver.py.
// A persistent headless Chromium; POST a JSON list of steps to http://127.0.0.1:9334/.
// Run from atlas/web so @playwright/test resolves: node ../docs/design/review-2026-10-12/measure/driver.mjs
import http from "node:http";
import { createRequire } from "node:module";
const require = createRequire(process.cwd() + "/package.json");
const { chromium } = require("@playwright/test");

const browser = await chromium.launch();
const S = {};

async function ensure(name, opts) {
  if (S[name]) return S[name];
  const ctx = await browser.newContext(opts);
  const pg = await ctx.newPage();
  const msgs = [];
  pg.on("console", (m) => msgs.push(`${m.type()}: ${m.text()}`));
  pg.on("pageerror", (e) => msgs.push(`pageerror: ${e}`));
  S[name] = { ctx, pg, msgs };
  return S[name];
}

async function step(c) {
  const name = c.ctx || "main";
  if (c.a === "new") {
    if (S[name]) { await S[name].ctx.close(); delete S[name]; }
    await ensure(name, c.opts || {});
    return "ok";
  }
  const { ctx, pg, msgs } = S[name];
  const loc = () => pg.locator(c.sel).first();
  switch (c.a) {
    case "goto": await pg.goto(c.url, { waitUntil: c.wait || "networkidle" }); return pg.url();
    case "click": await loc().click({ timeout: c.timeout || 5000 }); return "clicked";
    case "tap": await loc().tap({ timeout: 5000 }); return "tapped";
    case "fill": await loc().fill(c.text); return "filled";
    case "type": await pg.keyboard.type(c.text, { delay: c.delay ?? 30 }); return "typed";
    case "press": await pg.keyboard.press(c.key); return "pressed";
    case "select": return await loc().selectOption(c.value);
    case "wait": await pg.waitForTimeout(c.ms); return "waited";
    case "waitfor": await loc().waitFor({ state: c.state || "visible", timeout: c.timeout || 10000 }); return "found";
    case "scroll": await pg.evaluate((y) => window.scrollTo(0, y), c.y); await pg.waitForTimeout(400); return await pg.evaluate(() => window.scrollY);
    case "wheel": await pg.mouse.wheel(0, c.dy); await pg.waitForTimeout(400); return await pg.evaluate(() => window.scrollY);
    case "shot":
      if (c.sel) { await loc().screenshot({ path: c.path }); return c.path; }
      await pg.screenshot({ path: c.path, fullPage: !!c.full, ...(c.clip ? { clip: c.clip } : {}) });
      return c.path;
    case "eval": return await pg.evaluate(c.js);
    case "text": return await pg.locator(c.sel || "body").first().innerText();
    case "aria": return await pg.locator(c.sel || "body").first().ariaSnapshot();
    case "msgs": { const r = [...msgs]; msgs.length = 0; return r; }
    case "url": return pg.url();
    case "focus":
      return await pg.evaluate(() => {
        const e = document.activeElement; if (!e) return null; const b = e.getBoundingClientRect();
        return { tag: e.tagName, id: e.id, role: e.getAttribute("role"), name: e.getAttribute("aria-label") || e.innerText?.slice(0, 60), x: b.x, y: b.y, w: b.width, h: b.height };
      });
    case "mouse": await pg.mouse.click(c.x, c.y); return "mouse";
    case "close": await ctx.close(); delete S[name]; return "closed";
    default: return "unknown";
  }
}

http.createServer(async (req, res) => {
  let body = ""; for await (const ch of req) body += ch;
  let cmds = JSON.parse(body); if (!Array.isArray(cmds)) cmds = [cmds];
  const out = [];
  for (const c of cmds) {
    const t0 = Date.now();
    try { out.push({ r: await step(c), ms: Date.now() - t0 }); }
    catch (e) { out.push({ err: String(e).slice(0, 600) }); if (c.stop !== false) break; }
  }
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify(out));
}).listen(9334, "127.0.0.1", () => console.log("driver ready"));
