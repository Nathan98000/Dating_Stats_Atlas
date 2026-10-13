// m1: every page at every width, arriving cold (a fresh context, no cookie).
// Records: title, og/twitter tags, sideways scroll and clipped elements, page height,
// and the page weight by kind (HTML, JS, CSS, fonts, images, API, RSC prefetches):
// count and transfer bytes as the browser received them (encoded), plus decoded bytes.
// Screenshot of the first viewport for each page and width.
//   node m1_pages.mjs  -> m1_pages.json, shots/<page>-<width>-top.png
import { launch, BASE, PAGES, VIEWPORTS, settle, kind } from "./common.mjs";
import { mkdirSync, writeFileSync } from "fs";

mkdirSync("shots", { recursive: true });
const only = process.argv[2] ? process.argv[2].split(",") : null;
const browser = await launch();
const out = {};
for (const [w, opts] of Object.entries(VIEWPORTS)) {
  if (only && !only.includes(w)) continue;
  for (const [name, url] of Object.entries(PAGES)) {
    const ctx = await browser.newContext(opts);
    const page = await ctx.newPage();
    const reqs = [];
    page.on("requestfinished", async (req) => {
      try {
        const s = await req.sizes();
        const resp = await req.response();
        reqs.push({
          url: req.url().replace(BASE, ""),
          type: req.resourceType(),
          status: resp ? resp.status() : null,
          transfer: s.responseBodySize + s.responseHeadersSize,
          body: s.responseBodySize,
          enc: resp ? (await resp.allHeaders())["content-encoding"] || null : null,
        });
      } catch {}
    });
    const t0 = Date.now();
    const resp = await page.goto(BASE + url, { waitUntil: "load" });
    await settle(page, 400);
    const info = await page.evaluate(() => {
      const meta = {};
      document.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"], meta[name="description"], link[rel="canonical"]').forEach((m) => {
        meta[m.getAttribute("property") || m.getAttribute("name") || m.getAttribute("rel")] = m.getAttribute("content") || m.getAttribute("href");
      });
      const vw = document.documentElement.clientWidth;
      const clipped = [];
      for (const el of document.querySelectorAll("body *")) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        if (r.right > vw + 1 || r.left < -1) {
          // ignore when an ancestor clips or scrolls it on purpose
          let a = el.parentElement, ok = false;
          while (a && a !== document.body) {
            const cs = getComputedStyle(a);
            if (["hidden", "auto", "scroll", "clip"].includes(cs.overflowX)) {
              const ar = a.getBoundingClientRect();
              if (ar.right <= vw + 1 && ar.left >= -1) { ok = true; break; }
            }
            a = a.parentElement;
          }
          const cs = getComputedStyle(el);
          if (!ok && cs.visibility !== "hidden" && cs.position !== "fixed" && !el.closest("[aria-hidden=true].sr-only, .sr-only"))
            clipped.push(`${el.tagName.toLowerCase()}.${String(el.className).slice(0, 40)} [${Math.round(r.left)}..${Math.round(r.right)}] "${(el.innerText || "").slice(0, 30)}"`);
        }
      }
      const imgs = [...document.images].map((i) => ({
        src: i.currentSrc.replace(location.origin, ""), natural: `${i.naturalWidth}x${i.naturalHeight}`,
        shown: `${Math.round(i.getBoundingClientRect().width)}x${Math.round(i.getBoundingClientRect().height)}`,
        loading: i.loading, fetchpriority: i.getAttribute("fetchpriority"), alt: i.alt,
      }));
      return {
        title: document.title, meta, lang: document.documentElement.lang,
        h1: [...document.querySelectorAll("h1")].map((h) => h.innerText),
        scroll_width: document.documentElement.scrollWidth, client_width: vw,
        page_height: document.documentElement.scrollHeight,
        clipped: clipped.slice(0, 8), clipped_count: clipped.length, imgs,
      };
    });
    const weight = {};
    for (const r of reqs) {
      const k = kind(r.url, r.type);
      weight[k] = weight[k] || { count: 0, transfer: 0, body: 0 };
      weight[k].count++; weight[k].transfer += r.transfer; weight[k].body += r.body;
    }
    const total = Object.values(weight).reduce((n, v) => n + v.transfer, 0);
    out[`${name}@${w}`] = { url, status: resp ? resp.status() : null, ms_to_settle: Date.now() - t0, ...info, weight, total_transfer: total, requests: reqs };
    await page.screenshot({ path: `shots/${name}-${w}-top.png` });
    await ctx.close();
    process.stdout.write(`${name}@${w} ${Math.round(total / 1024)}KB sw=${info.scroll_width}/${info.client_width} clip=${info.clipped_count}\n`);
  }
}
await browser.close();
const file = only ? `m1_pages_${only.join("_")}.json` : "m1_pages.json";
writeFileSync(file, JSON.stringify(out, null, 1));
