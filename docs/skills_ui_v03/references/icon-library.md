# Icon library

Every pictorial mark on a cadence page is inline SVG. Never emoji, Unicode
dingbats (check marks, stars, arrows, bullets) or icon fonts; the validator
fails on them.

## Sprite pattern (used by the template)

Declare each glyph once as a `<symbol>` in a hidden sprite at the top of
`<body>`, then reference it anywhere:

```html
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
  <symbol id="i-inbox" viewBox="0 0 24 24"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>...</symbol>
</svg>

<svg class="i"><use href="#i-inbox"/></svg>
```

```css
.i{width:1em;height:1em;flex:none;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.i-fill{fill:currentColor;stroke:none}  /* star, play, pause */
```

- Lucide grammar: 24 viewBox, `currentColor`, stroke 1.75 (1.5-2 allowed),
  round caps and joins. Leave stroke attributes off the symbol children so the
  `.i` class controls them.
- Size with CSS (`width`/`height`); color always inherits.
- Decorative icons sit inside elements that carry the text; icon-only buttons
  get an `aria-label`.
- In React/Vue, use `lucide-react` / `lucide-vue-next` with the same stroke
  width instead of the sprite.

## Brand mark

The example brand mark is a light rounded tile with a dark open loop ending in
a dot and a small cyan center (symbol `#brand`, 32 viewBox). The same drawing
is the favicon as a `data:image/svg+xml` URI. Draw a new simple geometric mark
for each product; never borrow a real logo.

## Glyphs in the template

| Purpose | Symbol | Lucide name |
| --- | --- | --- |
| Inbox, Capture step | `i-inbox` | inbox |
| Themes, tags | `i-tag` | tag |
| Roadmap, Prioritize step | `i-kanban` | kanban |
| Loops | `i-loop` | refresh-cw |
| Digests, Follow up step | `i-send` | send |
| Customers chip | `i-users` | users |
| Accounts | `i-building` | building-2 |
| Search | `i-search` | search |
| Email source | `i-mail` | mail |
| Team chat source | `i-chat` | message-square |
| Help desk source | `i-headset` | headset |
| App reviews source | `i-phone-app` | smartphone |
| Call notes source | `i-phone` | phone |
| In-app widget source | `i-widget` | app-window |
| AI tags | `i-sparkles` | sparkles |
| Trend up / down | `i-up` / `i-down` | trending-up / trending-down |
| Checks in lists and tables | `i-check` | check |
| Chevrons | `i-chev-down` / `i-chev-right` / `i-updown` | chevron-down / chevron-right / chevrons-up-down |
| CTA arrows | `i-arrow-right` (`.i-arr` nudges on hover) | arrow-right |
| Accordion | `i-plus` (rotates 45deg when open) | plus |
| Close, menu | `i-x` / `i-menu` | x / menu |
| Security | `i-shield`, `i-lock`, `i-key`, `i-globe`, `i-history`, `i-user-check`, `i-db` | shield-check, lock, key-round, globe, history, user-check, database |
| Integrations | `i-webhook`, `i-code`, `i-list-checks`, `i-hash`, `i-briefcase` | webhook, code, list-checks, hash, briefcase |
| Product chip | `i-zap` | zap |
| Pricing chip | `i-receipt` | receipt |
| Calendar, filter, link, reply, merge | `i-calendar`, `i-filter`, `i-link`, `i-reply`, `i-merge` | calendar, list-filter, link, reply, git-merge |
| Keyboard hint | `i-cmd` + the letter in text | command |
| Status and errors | `i-circle-check`, `i-alert` | circle-check, circle-alert |
| Ratings | `i-star` with `.i-fill`, color `--star` | star |
| Slider control | `i-pause` / `i-play` with `.i-fill` | pause / play |
| Footer links | `i-rss`, `i-help`, `i-shield` | rss, circle-help, shield-check |
| Named cursors | inline path of mouse-pointer-2, filled | mouse-pointer-2 |

Path data for each symbol is in the sprite at the top of `template.html`.

## Fictional wordmarks (marquee)

Customer logos are typography plus a simple abstract mark, never real brand
SVGs:

```html
<span class="wm" style="font-weight:600;letter-spacing:.22em">SKERROW</span>
<span class="wm" style="font-weight:720;letter-spacing:-.045em">
  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" stroke-width="3.2"/></svg>pellaro</span>
```

Vary weight, tracking, case, italic or mono per mark so the row reads as six
to eight different companies. Marks are single geometric ideas (a ring, two
triangles, a split circle, a 2x2 grid, a plus in a rounded square). Color
`#7f8a94`, lifting to `--text` on hover.

## People

- **Spotlight and story people** get generated portraits (see
  [image-plan.md](image-plan.md)): circles, `object-position: 50% 30%`.
- **Product UI people and the quote wall** use initials avatars (`.av`):
  1-2 letters, weight 650, light text on a deep two-stop gradient set per
  person with `--h1`/`--h2`; keep the same colors for the same person
  everywhere on the page.
