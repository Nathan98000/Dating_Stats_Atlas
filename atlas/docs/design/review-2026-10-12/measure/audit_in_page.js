// Injected into the page by m4_sizes.mjs. Returns: interactive targets smaller than 44x44,
// text smaller than 12px, text contrast below its WCAG AA threshold measured where it is
// used (its own colour on the first opaque background behind it), and control boundaries
// below 3:1 against what surrounds them.
(() => {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const L = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = L(a), y = L(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const blend = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity === 0) return false;
    if (el.closest(".sr-only")) return false;
    // inside a closed dialog/details or an aria-hidden popover that is not shown
    let a = el;
    while (a) { const s = getComputedStyle(a); if (s.display === "none" || s.visibility === "hidden") return false; a = a.parentElement; }
    return true;
  };
  const bgOf = (el) => {
    let a = el, stack = [];
    while (a) {
      const cs = getComputedStyle(a);
      if (cs.backgroundImage && cs.backgroundImage !== "none" && !cs.backgroundImage.startsWith("linear-gradient")) return { over: "image" };
      if (a.tagName === "IMG") return { over: "image" };
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; }
      a = a.parentElement;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) base = blend(stack[i], base);
    return { c: base };
  };
  const name = (el) => (el.getAttribute("aria-label") || el.innerText || el.value || el.getAttribute("title") || "").trim().replace(/\s+/g, " ").slice(0, 40);
  const path = (el) => {
    const t = el.closest("[data-testid]");
    return `${el.tagName.toLowerCase()}${el.id ? "#" + el.id.slice(0, 20) : ""}${t ? " in [" + t.dataset.testid + "]" : ""}`;
  };

  // 1. targets
  const sel = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=radio], [role=option], [role=tab], [role=checkbox], [role=switch], [tabindex]:not([tabindex="-1"])';
  const small = [];
  const seen = new Set();
  for (const el of document.querySelectorAll(sel)) {
    if (!visible(el)) continue;
    // a checkbox/radio inside a label: the label is the target
    let t = el;
    if ((el.type === "checkbox" || el.type === "radio") && el.closest("label")) t = el.closest("label");
    if (seen.has(t)) continue; seen.add(t);
    const r = t.getBoundingClientRect();
    if (r.width < 44 - 0.5 || r.height < 44 - 0.5) {
      // inline links inside running text are a recognised exception
      const inline = t.tagName === "A" && getComputedStyle(t).display === "inline" && t.parentElement && /\S/.test((t.parentElement.innerText || "").replace(t.innerText, ""));
      small.push({ el: path(t), name: name(t), w: Math.round(r.width), h: Math.round(r.height), inline_in_text: !!inline, y: Math.round(r.top + scrollY) });
    }
  }

  // 2 + 3. text size and contrast
  const tiny = [], low = [], overImage = [];
  const doneText = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (!n.nodeValue.trim()) continue;
    const el = n.parentElement;
    if (!el || doneText.has(el) || !visible(el)) continue;
    if (["SCRIPT", "STYLE", "NOSCRIPT", "OPTION"].includes(el.tagName)) continue;
    doneText.add(el);
    const cs = getComputedStyle(el);
    const size = parseFloat(cs.fontSize), weight = +cs.fontWeight || 400;
    const text = n.nodeValue.trim().slice(0, 40);
    if (size < 12) tiny.push({ el: path(el), text, size });
    const fg = parse(cs.color);
    const bg = bgOf(el);
    if (bg.over === "image") { overImage.push({ el: path(el), text }); continue; }
    if (!fg) continue;
    const col = fg.a < 1 ? blend(fg, bg.c) : fg;
    const r = ratio(col, bg.c);
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3 : 4.5;
    const disabled = el.closest("[disabled], [aria-disabled=true]");
    if (r < need - 0.005 && !disabled) low.push({ el: path(el), text, size, weight, ratio: +r.toFixed(2), need, fg: cs.color, bg: `rgb(${Math.round(bg.c.r)}, ${Math.round(bg.c.g)}, ${Math.round(bg.c.b)})` });
  }

  // 4. control boundaries (1.4.11): border colour against the background behind the control
  const bounds = [];
  for (const el of document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]), select, textarea, button, [role=radio], [role=checkbox], label:has(> input[type=checkbox])')) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const bw = parseFloat(cs.borderTopWidth);
    const outer = bgOf(el.parentElement || el);
    if (outer.over === "image") continue;
    const own = parse(cs.backgroundColor);
    const fill = own && own.a > 0 ? blend(own, outer.c) : outer.c;
    const fillRatio = ratio(fill, outer.c);
    if (bw > 0 && cs.borderTopStyle !== "none") {
      const bc = parse(cs.borderTopColor);
      if (!bc || bc.a === 0) continue;
      const r = ratio(bc.a < 1 ? blend(bc, outer.c) : bc, outer.c);
      if (r < 3 && fillRatio < 3) bounds.push({ el: path(el), name: name(el), border: cs.borderTopColor, behind: `rgb(${Math.round(outer.c.r)}, ${Math.round(outer.c.g)}, ${Math.round(outer.c.b)})`, ratio: +r.toFixed(2), fill_ratio: +fillRatio.toFixed(2), checked: el.getAttribute("aria-checked") || el.getAttribute("aria-pressed") || null });
    }
  }
  return { small_targets: small, tiny_text: tiny, low_contrast: low, text_over_images: overImage, weak_boundaries: bounds };
})();
