#!/usr/bin/env node
/**
 * Build a standalone page: inline every local asset referenced as images/...,
 * fonts/... or assets/... (relative to the source file) as a base64 data URI,
 * and embed fontsource CDN font files
 * (https://cdn.jsdelivr.net/fontsource/fonts/...woff2, as used by the
 * template's @font-face rules) by downloading them once at build time.
 *
 *   node scripts/inline-assets.mjs path/to/source.html path/to/page.html
 *
 * Works on src="", href="", url(...) and quoted strings inside scripts. Reports
 * the weight of each asset and fails when a referenced file is missing or a
 * CDN font cannot be downloaded.
 *
 * Embed once: an image used by several <img> slots (a portrait in a team chip,
 * a project lead on Home, Work and its case page) is embedded only in its first
 * <img>, which gets data-imgkey="<key>". Every repeat keeps a 1 px placeholder
 * plus data-imgref="<key>", and a three-line script before </body> copies the
 * first source into it at load. Without JavaScript the first copy still shows;
 * only repeats stay blank, the page's one JavaScript dependency for images.
 * Pass --no-dedupe to keep every copy inline instead (bigger file).
 */
import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createHash } from "node:crypto";

const args = process.argv.slice(2);
const dedupe = !args.includes("--no-dedupe");
const [src, out] = args.filter((a) => !a.startsWith("--"));
if (!src || !out) {
  console.error("usage: node scripts/inline-assets.mjs <source.html> <page.html> [--no-dedupe]");
  process.exit(2);
}
const base = dirname(resolve(src));
const types = {
  webp: "image/webp", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", svg: "image/svg+xml",
  avif: "image/avif", gif: "image/gif", woff2: "font/woff2", woff: "font/woff", mp4: "video/mp4",
};
const used = new Map();
const missing = new Set();
let html = readFileSync(src, "utf8");

/* CDN fonts: download each fontsource woff2 once and embed it. */
const cdnFonts = [...new Set(html.match(/https:\/\/cdn\.jsdelivr\.net\/fontsource\/fonts\/[A-Za-z0-9._:@\/-]+\.woff2/g) || [])];
for (const url of cdnFonts) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    html = html.split(url).join(`data:font/woff2;base64,${buf.toString("base64")}`);
    console.log(`${String(Math.round(buf.length / 1024)).padStart(6)} KB  ${url}`);
  } catch (err) {
    missing.add(`${url} (${err.message}; download it into fonts/ and point the @font-face src at fonts/<file>.woff2)`);
  }
}

html = html.replace(
  /(["'(])((?:\.\/)?(?:images|fonts|assets)\/[A-Za-z0-9._\/-]+\.(webp|png|jpe?g|svg|avif|gif|woff2?|mp4))(?=["')])/g,
  (all, q, path, ext) => {
    const f = resolve(base, path);
    if (!existsSync(f)) { missing.add(path); return all; }
    used.set(path, (used.get(path) || 0) + 1);
    return q + `data:${types[ext.toLowerCase()]};base64,` + readFileSync(f).toString("base64");
  },
);
/* Embed each repeated image once. */
if (dedupe) {
  const re = /(<img\b[^>]*?\s)src="(data:image\/[a-z+]+;base64,[A-Za-z0-9+/=]+)"/g;
  const seen = new Map();
  for (const m of html.matchAll(re)) seen.set(m[2], (seen.get(m[2]) || 0) + 1);
  const keys = new Map();
  let saved = 0;
  for (const [uri, n] of seen) {
    if (n < 2 || uri.length < 2048) continue;
    keys.set(uri, "i" + createHash("sha1").update(uri).digest("hex").slice(0, 8));
    saved += uri.length * (n - 1);
  }
  if (keys.size) {
    const first = new Set();
    const blank = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
    html = html.replace(re, (all, pre, uri) => {
      if (!keys.has(uri)) return all;
      const k = keys.get(uri);
      if (!first.has(uri)) { first.add(uri); return `${pre}src="${uri}" data-imgkey="${k}"`; }
      return `${pre}src="${blank}" data-imgref="${k}"`;
    });
    const boot = `<script>/* shared images: each file is embedded once (data-imgkey); repeats copy its source */(function(){var M={},S=document.querySelectorAll('img[data-imgkey]'),L=document.querySelectorAll('img[data-imgref]'),i;for(i=0;i<S.length;i++)M[S[i].getAttribute('data-imgkey')]=S[i].getAttribute('src');for(i=0;i<L.length;i++){var k=L[i].getAttribute('data-imgref');if(M[k])L[i].src=M[k];}})();</script>\n`;
    const at = html.lastIndexOf("</body>");
    if (at < 0) { missing.add("</body> (needed for the shared-image script)"); }
    else html = html.slice(0, at) + boot + html.slice(at);
    console.log(`embed once: ${keys.size} repeated images stored once, saved ${(saved / 1048576).toFixed(2)} MB`);
  }
}
writeFileSync(out, html);
for (const [p, n] of used) {
  const kb = Math.round(statSync(resolve(base, p)).size / 1024);
  console.log(`${String(kb * n).padStart(6)} KB  ${n > 1 ? `(x${n}) ` : ""}${p}`);
}
const mb = statSync(out).size / 1048576;
console.log(`wrote ${out}: ${mb.toFixed(2)} MB${mb > 5 ? "  (over the 5 MB target)" : ""}`);
if (missing.size) {
  console.error(`missing: ${[...missing].join(", ")}`);
  process.exit(1);
}
