#!/usr/bin/env node
/**
 * Validate a cadence marketing site built from this Skill.
 *
 *   node scripts/validate-cadence.mjs path/to/index.html            # your finished page (default)
 *   node scripts/validate-cadence.mjs path/to/index.src.html --source
 *   node scripts/validate-cadence.mjs path/to/index.html --files
 *   node scripts/validate-cadence.mjs references/template.html --template
 *   node scripts/validate-cadence.mjs path/to/store-demo.html --demo
 *
 * Modes
 *   (default)   A finished single-file page for a real brief. Strict: offline,
 *               every asset inlined, no REPLACE slots, and it FAILS when the
 *               template's sample identity is still in the page (product
 *               brand, customer workspace, people, customer companies,
 *               sample domains). Comments count.
 *   --source    Your source page before scripts/inline-assets.mjs: relative
 *               images/, fonts/, assets/ paths and the fontsource CDN woff2
 *               files inside @font-face src are allowed; every other check,
 *               including REPLACE slots and sample leftovers, still runs.
 *   --files     A deployed site that keeps its images and fonts as local files
 *               beside the page (images/, fonts/, assets/): local references
 *               and size are not checked; remote URLs (fonts included) and
 *               sample leftovers still fail.
 *   --template  references/template.html itself: like --source, plus REPLACE
 *               comments and the sample identity are allowed.
 *   --demo      The fictional store demo: strict like the default, but the
 *               sample identity is allowed because the demo is the sample.
 *   (--in-project is kept as an alias of --files.)
 *
 * No section, heading, route name or count from the sample is required; the
 * checks are structural:
 *   1. Self-contained and offline (per mode): no remote URLs, scripts,
 *      stylesheets or fonts; no un-inlined local assets in a single file.
 *   2. Sandbox-safe: no network APIs, alert/confirm/prompt, window.open or top
 *      navigation; storage only inside try/catch.
 *   3. No emoji or Unicode dingbats; pictorial marks are inline SVG.
 *   4. Content hygiene: no REPLACE slots (except --template), no lorem ipsum
 *      or generic placeholder names.
 *   5. Structure: head metadata, landmarks, skip link, router with a home and
 *      a 404 route, one h1 per route, every in-page anchor and #/ route link
 *      resolves, labelled form controls, the signature cadence components,
 *      tokens, reveal system with a no-JS fallback, prefers-reduced-motion,
 *      :focus-visible, @font-face.
 *   6. Pricing (when present): two to four tiers, data-count set for fewer
 *      than four, every switchable price has both monthly and yearly values.
 *   7. Images: every <img> has alt and width/height; below-the-fold lazy.
 *   8. Copy tells: em and en dashes in visible text (warning).
 *   9. Size: warn above 5 MB, fail above 8 MB (single file only).
 *  10. Sample leftovers (default, --source and --files).
 */
import { readFileSync, statSync } from "node:fs";

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith("--"));
const isTemplate = args.includes("--template");
const isDemo = args.includes("--demo") && !isTemplate;
const isSource = args.includes("--source") && !isTemplate;
const isFiles = (args.includes("--files") || args.includes("--in-project")) && !isTemplate && !isSource;
const allowCdnFonts = isTemplate || isSource; /* pre-build pages still load the fontsource CDN files */
const allowLocal = isTemplate || isSource || isFiles; /* images/, fonts/, assets/ beside the page */
const checkLeftovers = !isTemplate && !isDemo;
const mode = isTemplate ? "template" : isDemo ? "demo" : isSource ? "source" : isFiles ? "files" : "site";
if (!file) {
  console.error("usage: node scripts/validate-cadence.mjs <page.html> [--source | --files | --template | --demo]");
  process.exit(2);
}

/* The template's sample identity (Loopwright, a fictional feedback product, and
   its customer workspace Fernhold). A buyer's page must not contain any of
   these; the template and the store demo may. Case-insensitive, whole words. */
const SAMPLE = {
  brand: ["Loopwright", "loopwright.example", "Fernhold", "fernhold.example"],
  people: [
    "Amara Okafor", "Tomás Rivera", "Ingrid Halvorsen",
    "Jonas Weber", "Dev Malhotra", "Elena Marsh", "Mei Tan", "Priscilla Nwosu",
    "Clara Lindqvist", "Rafael Souza", "Ben Hollis",
    "Priya Raman", "Daniel Osei", "Lena Fischer", "Marcus Chen", "Sofia Marin", "Noah Adeyemi", "Yuki Tanaka",
    "Hannah Weiss", "Ravi Menon", "Chloe Martin", "Omar Haddad",
  ],
  companies: [
    "Halcyon Freight", "Fenwyn Labs", "Arbor & Vale", "Quarry Studio", "Sable Logistics", "Pinecrest Clinics",
    "Juniper Schools", "Pellaro", "Lumiwen", "Voltrane", "Tessavo", "Skerrow", "Ottavine", "Wendmere",
  ],
  /* first names alone are only a warning: they may belong to the buyer's own people */
  firstNames: ["Amara", "Tomás", "Ingrid", "Maya", "Jonas"],
};

let html;
try {
  html = readFileSync(file, "utf8");
} catch (err) {
  console.error(`cannot read ${file}: ${err.message}`);
  process.exit(2);
}

const errors = [];
const warn = [];
const fail = (m) => errors.push(m);

const noData = html.replace(/data:[a-z0-9/+.-]+;base64,[A-Za-z0-9+/=]+/gi, "data:");
const scripts = [...noData.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]).join("\n");
const styles = [...noData.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).join("\n");
const markup = noData
  .replace(/<!--[\s\S]*?-->/g, "")
  .replace(/<script\b[\s\S]*?<\/script>/gi, "")
  .replace(/<style\b[\s\S]*?<\/style>/gi, "");
const text = markup.replace(/<[^>]+>/g, " ");

/* 1. self-contained */
const CDN_FONT = /url\(\s*(["']?)https:\/\/cdn\.jsdelivr\.net\/fontsource\/fonts\/[^)"'\s]+\.woff2\1\s*\)/g;
const REMOTE_URL = /url\(\s*["']?(?:https?:)?\/\/[^)]*\)/gi;
/* remote @font-face files are reported once below; the other checks look at the rest */
const netHtml = noData.replace(/@font-face\s*\{[^}]*\}/g, (block) => block.replace(allowCdnFonts ? CDN_FONT : REMOTE_URL, "url()"));
if (!allowCdnFonts && /@font-face\s*\{[^}]*https?:\/\/[^}]*\}/.test(noData)) {
  fail(isFiles
    ? "@font-face loads a remote font file; download the two fontsource woff2 files into fonts/ beside the page and point src at them"
    : "@font-face loads a remote font file; build with scripts/inline-assets.mjs to embed it as a data URI");
}
for (const m of netHtml.matchAll(/(?<![\w-])(?:src|href|poster|srcset|action)\s*=\s*["']\s*((?:https?:)?\/\/[^"']+)["']/gi)) {
  fail(`external reference not allowed: ${m[1].slice(0, 80)}`);
}
if (/url\(\s*["']?(?:https?:)?\/\//i.test(netHtml)) fail("CSS url() references a remote asset");
if (/@import\s+(?:url\(\s*)?["']?(?:https?:)?\/\//i.test(netHtml)) fail("remote CSS @import is not allowed");
if (/<script[^>]+\bsrc\s*=/i.test(noData)) fail("external <script src> is not allowed; inline all JS");
if (/<link[^>]+rel=["']?(?:stylesheet|preload|preconnect|dns-prefetch)/i.test(noData)) fail("external <link> (stylesheet/preload/preconnect) is not allowed; inline all CSS");
if (!allowLocal) {
  const rel = noData.match(/["'(]\.?\/?(?:images|fonts|assets)\/[A-Za-z0-9._\/-]+\.(?:webp|png|jpe?g|svg|avif|woff2?|mp4|gif)/i);
  if (rel) fail(`relative asset path left in a single-file page (${rel[0].slice(1)}); build with scripts/inline-assets.mjs, or validate a deployed site with --files`);
}

/* 2. sandbox-safe APIs */
for (const api of ["fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "navigator.sendBeacon", "indexedDB", "document.cookie"]) {
  if (scripts.includes(api)) fail(`forbidden API in a sandboxed page: ${api}`);
}
for (const [re, label] of [
  [/\balert\s*\(/, "alert()"],
  [/\bconfirm\s*\(/, "confirm()"],
  [/(?<![.\w])prompt\s*\(/, "prompt()"],
  [/window\.open\s*\(/, "window.open()"],
  [/\b(?:window\.)?top\.location/, "top navigation"],
]) {
  if (re.test(scripts)) fail(`${label} is not allowed (sandboxed iframe, no popups or top navigation)`);
}
if (/\b(?:localStorage|sessionStorage)\b/.test(scripts) && !/try\s*\{[^}]*\b(?:localStorage|sessionStorage)\b/.test(scripts)) {
  fail("storage access must be wrapped in try/catch with an in-memory fallback");
}
if (/target=["']_(?:blank|top|parent)["']/.test(markup)) warn.push('target="_blank/_top/_parent" opens a popup or navigates the top frame, which a sandboxed iframe blocks');

/* 3. emoji / dingbats */
const emojiRe = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{FE0F}\u{25A0}-\u{25FF}\u{2700}-\u{27BF}\u{2022}\u{2023}\u{2043}]/u;
const emojiHit = text.match(emojiRe) || scripts.match(emojiRe);
if (emojiHit) fail(`emoji or dingbat character found ("${emojiHit[0]}"); use inline Lucide-style SVG instead`);

/* 4. placeholders */
if (!isTemplate && /REPLACE/.test(noData)) fail("leftover REPLACE slot comment from the template: fill the slot and delete the comment");
if (/lorem ipsum|dolor sit amet|your company|jane doe|john doe/i.test(text)) fail("placeholder copy found (lorem ipsum / Your Company / Jane Doe)");

/* 5. structure */
const need = [
  [/<html[^>]+lang=/, "a lang attribute on <html>"],
  [/<title>[^<]{3,}<\/title>/, "a non-empty <title>"],
  [/<meta[^>]+name=["']description["']/, "a meta description"],
  [/<meta[^>]+name=["']viewport["']/, "a viewport meta"],
  [/<meta[^>]+property=["']og:title["']/, "Open Graph tags"],
  [/<link[^>]+rel=["']icon["'][^>]+href=["']data:/, "an inline SVG favicon (data: URI)"],
  [/<header\b/, "a <header> landmark"],
  [/<nav\b/, "a <nav> landmark"],
  [/<main\b/, "a <main> landmark"],
  [/<footer\b/, "a <footer>"],
  [/class=["'][^"']*\bskip\b/, "a skip link (.skip)"],
  [/<h1\b/, "an h1"],
  [/class=["'][^"']*\bnav-pill\b/, "floating pill nav (.nav-pill)"],
  [/class=["'][^"']*\bhero\b/, "hero section (.hero)"],
  [/class=["'][^"']*\btilt-card\b/, "3D tilt product card (.tilt-card)"],
  [/class=["'][^"']*\bambient\b/, "ambient light shafts (.ambient)"],
  [/class=["'][^"']*\bmeteor\b/, "meteor beam accent (.meteor)"],
  [/class=["'][^"']*\bchip3d\b/, "3D section icon chip (.chip3d)"],
  [/class=["'][^"']*\bgrad\b/, "gradient heading class (.grad)"],
  [/class=["'][^"']*\bmac-lid\b/, "CSS MacBook lid (.mac-lid)"],
  [/--bg\s*:/, "design token --bg"],
  [/--accent\s*:/, "design token --accent"],
  [/--ease-out\s*:/, "motion token --ease-out"],
  [/IntersectionObserver/, "scroll-reveal system (IntersectionObserver)"],
  [/\.js\s+\.rv\b/, "reveal styles scoped under .js (content visible without JS)"],
  [/@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)/, "a prefers-reduced-motion: reduce block"],
  [/:focus-visible/, ":focus-visible styles"],
  [/@font-face/, "an @font-face declaration (Geist or the brand face)"],
];
for (const [re, label] of need) if (!re.test(noData)) fail(`missing required structure: ${label}`);
if (/<a\b[^>]*href=["']#["']/.test(markup)) fail('dead link href="#"; point every link at a section or route');

/* routes: the names are the buyer's own; only home and 404 are required */
const routeList = [...markup.matchAll(/data-route=["']([^"']+)["']/g)].map((m) => m[1]);
const routes = new Set(routeList);
for (const r of routeList.filter((r, i) => routeList.indexOf(r) !== i)) fail(`duplicate data-route="${r}"`);
if (!routes.has("home")) fail('router route missing: data-route="home"');
if (routes.size > 1 && !routes.has("404")) fail('router route missing: data-route="404" (unknown hashes fall back to it)');
const blocks = [...markup.matchAll(/<div class="route"[^>]*data-route="([^"]+)"[\s\S]*?(?=<div class="route"[^>]*data-route=|<\/main>)/g)];
for (const m of blocks) {
  const n = (m[0].match(/<h1\b/g) || []).length;
  if (n !== 1) fail(`route "${m[1]}" has ${n} <h1> (expected 1)`);
}
if (!blocks.length && (markup.match(/<h1\b/g) || []).length !== 1) fail("a page without routes must contain exactly one h1");
const ids = new Set([...markup.matchAll(/\bid=["']([^"']+)["']/g)].map((m) => m[1]));
for (const m of markup.matchAll(/<a\b[^>]*\bhref=["']#([^"']*)["']/g)) {
  const h = m[1];
  if (!h || h === "/") continue;
  if (h.startsWith("/")) {
    const path = h.slice(1).replace(/\/+$/, "");
    const first = path.split("/")[0];
    /* resolves when it names a route, or the router script knows the path (e.g. SITE.storySlug) */
    if (!routes.has(first) && !routes.has(path) && !scripts.includes(`'${path}'`) && !scripts.includes(`"${path}"`) && !scripts.includes(`'/${path}'`)) {
      fail(`link "#${h}" resolves to no route (data-route or a path the router parses)`);
    }
  } else if (!ids.has(decodeURIComponent(h))) {
    fail(`in-page link "#${h}" has no element with that id`);
  }
}
for (const m of markup.matchAll(/<(input|select|textarea)\b([^>]*)>/gi)) {
  const attrs = m[2];
  if (/type\s*=\s*["'](hidden|radio|checkbox|submit|button)["']/.test(attrs)) continue;
  const id = (attrs.match(/\bid\s*=\s*["']([^"']+)["']/) || [])[1];
  const labelled = /aria-label(?:ledby)?\s*=/.test(attrs) || (id && new RegExp(`for\\s*=\\s*["']${id}["']`).test(markup));
  if (!labelled) fail(`form control without a label: ${m[0].slice(0, 80)}`);
}

/* 6. pricing (optional section) */
const tiersTag = markup.match(/<div class="tiers\b[^"]*"[^>]*>/);
if (tiersTag) {
  const block = (markup.slice(tiersTag.index).match(/^[\s\S]*?(?:<div class="price-foot"|<\/section>)/) || [""])[0];
  const n = (block.match(/<article class="tier\b/g) || []).length;
  const dc = (tiersTag[0].match(/data-count=["'](\d)["']/) || [])[1];
  if (n < 2 || n > 4) fail(`pricing has ${n} tiers (the grid is built for two to four)`);
  else if (n < 4 && dc !== String(n)) warn.push(`pricing has ${n} tiers: set data-count="${n}" on .tiers so the grid centres them`);
  if (/data-monthly=/.test(block)) {
    for (const t of block.matchAll(/<[^>]*data-monthly=[^>]*>/g)) if (!/data-yearly=/.test(t[0])) fail(`price element has data-monthly but no data-yearly: ${t[0].slice(0, 80)}`);
  }
}

/* 7. images */
const imgs = [...markup.matchAll(/<img\b[^>]*>/gi)].map((m) => m[0]);
imgs.forEach((tag, i) => {
  if (!/\balt\s*=/.test(tag)) fail(`<img> #${i + 1} has no alt attribute`);
  if (!/\bwidth\s*=/.test(tag) || !/\bheight\s*=/.test(tag)) warn.push(`<img> #${i + 1} has no width/height (layout shift)`);
});
const lazy = imgs.filter((t) => /loading=["']lazy/.test(t)).length;
if (imgs.length > 2 && lazy === 0) warn.push('no below-the-fold image uses loading="lazy"');

/* 8. copy tells */
const dashes = (text.match(/[—–]|&mdash;|&ndash;/g) || []).length;
if (dashes) warn.push(`${dashes} em/en dash(es) in visible copy; rewrite with periods, commas or colons`);

/* 9. size */
const bytes = statSync(file).size;
if (!allowLocal) {
  if (bytes > 8 * 1024 * 1024) fail(`file is ${(bytes / 1048576).toFixed(2)} MB; the hard cap is 8 MB (build with scripts/inline-assets.mjs, which embeds each repeated image once)`);
  else if (bytes > 5 * 1024 * 1024) warn.push(`file is ${(bytes / 1048576).toFixed(2)} MB; aim for 5 MB or less`);
}

/* 10. sample leftovers: a buyer's page must not ship the template's identity */
if (checkLeftovers) {
  const ENT = { "&amp;": "&", "&aacute;": "á", "&#225;": "á", "&nbsp;": " ", "&rsquo;": "'", "&#39;": "'", "&apos;": "'" };
  const hay = noData.replace(/&(?:amp|aacute|#225|nbsp|rsquo|#39|apos);/g, (e) => ENT[e]).replace(/\s+/g, " ");
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "\\s+");
  const has = (term) => new RegExp(`(?<![\\p{L}\\p{N}])${esc(term)}(?![\\p{L}\\p{N}])`, "iu").test(hay);
  const found = [];
  for (const kind of ["brand", "people", "companies"]) for (const term of SAMPLE[kind]) if (has(term)) found.push(`${term} (${kind})`);
  if (found.length) fail(`sample identity from the template is still in the page: ${found.join(", ")}`);
  const visText = text.replace(/&aacute;/g, "á");
  for (const n of SAMPLE.firstNames) if (new RegExp(`(?<!\\p{L})${n}(?!\\p{L})`, "u").test(visText)) warn.push(`sample first name "${n}" appears: confirm it belongs to this brief`);
  const domains = [...new Set(noData.match(/\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.example\b/gi) || [])];
  if (domains.length) warn.push(`placeholder domain(s) ${domains.join(", ")}: list them for the user to replace with the real domain`);
}

for (const w of new Set(warn)) console.warn(`warn: ${w}`);
errors.splice(0, errors.length, ...new Set(errors));
if (errors.length) {
  for (const e of errors) console.error(`fail: ${e}`);
  console.error(`\n${errors.length} check(s) failed for ${file} [${mode} mode]`);
  process.exit(1);
}
console.log(`ok: ${file} passes all cadence landing checks [${mode} mode] (${routes.size} routes, ${imgs.length} images, ${(bytes / 1024).toFixed(0)} KB)`);
