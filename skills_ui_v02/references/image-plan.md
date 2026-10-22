# Cadence image plan

The hero image is the product, built in HTML/CSS/SVG. Photography is used only
where a real software company would use it: people behind customer quotes and
an editorial customer story. Five role-based photos plus five small hero
proof-row headshots cover the whole site; do not add stock photos of laptops,
abstract 3D blobs, or screenshots inside photos.

## Art direction (one photographer, one set)

> Low-key cinematic photograph with a cool graphite and charcoal palette, one faint cyan-teal practical light as the only color accent, soft directional key light, shot on a 50mm lens at f/2 on medium format digital, gentle fine film grain, natural unretouched skin, calm and focused mood, modern minimal studio interiors, no readable text anywhere, no logos, no visible screen content.

Why: the ground is charcoal and the accent is cyan, so photos are low-key and
graphite with a single faint cyan practical light. They sit in the page
without bright rectangles breaking the dark rhythm, and the portraits share
one backdrop and lighting so the spotlight reads as one series.

## Slots

| id | Role | Aspect and width | Crop focus | Used in |
| --- | --- | --- | --- | --- |
| `portrait-amara` | Spotlight portrait 1, story pull quote, app user avatar | 1:1, 640px | face upper third, object-position 50% 30% | Spotlight halo (96px), pill (38px), hero sidebar user (26px), story pull quote (44px) |
| `portrait-tomas` | Spotlight portrait 2 | 1:1, 640px | face upper third, object-position 50% 30% | Spotlight halo and pill |
| `portrait-ingrid` | Spotlight portrait 3, sign-in quote | 1:1, 640px | face upper third, object-position 50% 30% | Spotlight halo and pill, sign-in quote avatar |
| `story-team` | Customer story editorial (hero of the story) | 3:2, 1800px | people in the left two thirds; object-position 28% 50% in the home card, 40% 45% in the 21:9 story cover | Home story card (left half), story route cover |
| `story-detail` | Story detail / sign-in atmosphere | 3:2, 1200px | cards and hands centered; object-position 35% 50% on the sign-in panel | Story route figure, sign-in side panel |
| `ava-jonas` | Hero proof-row headshot (Jonas Weber) | 1:1, 240px | face centered, object-position 50% 32% | Hero proof row (56px tile) |
| `ava-dev` | Hero proof-row headshot (Dev Malhotra) | 1:1, 240px | face centered, object-position 50% 32% | Hero proof row (56px tile) |
| `ava-elena` | Hero proof-row headshot (Elena Marsh) | 1:1, 240px | face centered, object-position 50% 32% | Hero proof row (56px tile) |
| `ava-mei` | Hero proof-row headshot (Mei Tan) | 1:1, 240px | face centered, object-position 50% 32% | Hero proof row (56px tile) |
| `ava-priscilla` | Hero proof-row headshot (Priscilla Nwosu) | 1:1, 240px | face centered, object-position 50% 32% | Hero proof row (56px tile) |

Rules for every slot:
- `object-fit: cover` with the object-position above; no cut-off heads.
- `alt` describes the subject in context ("Fernhold's product team reviewing
  clusters of customer feedback cards"); purely decorative uses get `alt=""`.
- `width`/`height` attributes always; `loading="lazy"` and `decoding="async"`
  for everything below the hero.
- Portraits are generated people. Re-generate them for the user's own
  customers (or reuse the shipped ones as stand-ins with new names, see
  below); never use photos of real people without permission.
- No text, logos or readable UI in any photo.

## Re-theming for a new product

Keep the same roles and the same art direction, change the subjects:
- Portraits: the three spotlight customers (match their roles and the
  product's market; vary age, gender and background).
- Story editorial: the customer team doing the work the product helps with
  (a support pod, a clinic front desk, a warehouse floor), at blue hour.
- Story detail: a close-up of the physical side of that work.
- Proof-row headshots: the five customers quoted in the wall.

Priority when you cannot generate all ten:
1. `story-team` and `story-detail`: they show the sample product's work (a
   team at a wall of feedback index cards, hands sorting index cards) and
   must always be regenerated for another business.
2. The three spotlight portraits (`portrait-*`).
3. The five proof-row headshots (`ava-*`).
The shipped portraits and headshots are generic studio portraits on the same
graphite backdrop: you may reuse them as stand-ins, but give the people new
names in `WALL`, `SPOT` and the markup (the sample names fail the validator)
and tell the user they are generated stand-ins. For a real company's real
customers or team, ask for their photos.

Repeated slots cost nothing extra: `scripts/inline-assets.mjs` embeds each
image file once and the repeats (the 26px sidebar avatar, the pill, the pull
quote) copy it at load.

If no image tool is available, keep the slots, ship the product UI and the
initials avatars (`.av`), and tell the user which slots still need photos.

## Exact prompts used in the demo

Each prompt is followed by the art-direction sentence above.

**portrait-amara** (square, 640px)

> Head-and-shoulders portrait of a woman in her late thirties of West African descent with short natural hair, wearing a charcoal wool crewneck sweater, looking just off camera with a composed, warm half smile. Subject centered with comfortable space above the head and shoulders fully in frame. Seamless dark graphite studio backdrop with a subtle gradient, soft key light from camera left, faint cyan rim light tracing her right shoulder.

**portrait-tomas** (square, 640px)

> Head-and-shoulders portrait of a man in his early thirties of Latin American descent with short dark hair and a neatly trimmed beard, wearing a black cotton overshirt over a grey t-shirt, relaxed friendly expression looking just off camera. Subject centered with comfortable space above the head and shoulders fully in frame. Seamless dark graphite studio backdrop with a subtle gradient, soft key light from camera left, faint cyan rim light tracing his right shoulder.

**portrait-ingrid** (square, 640px)

> Head-and-shoulders portrait of a Scandinavian woman in her mid forties with shoulder-length ash blonde hair and thin round metal glasses, wearing a dark navy blazer over a black top, thoughtful confident expression looking just off camera. Subject centered with comfortable space above the head and shoulders fully in frame. Seamless dark graphite studio backdrop with a subtle gradient, soft key light from camera left, faint cyan rim light tracing her right shoulder.

**story-team** (landscape, 1800px)

> Candid documentary photograph of a product team of four colleagues in their thirties standing in front of a large dark wall covered with pinned white paper index cards arranged in loose clusters, inside a dim modern studio office at blue hour. One woman points at a cluster of cards while the others listen, one holds a ceramic coffee mug. The cards carry only faint illegible pencil marks. Large window on the right with deep blue dusk light, a single desk lamp casting a soft cyan-tinted glow. Framed from the waist up at a slight distance, people occupy the center and left two thirds, calm collaborative mood.

**story-detail** (landscape, 1200px)

> Overhead close-up of two pairs of hands sorting white paper index cards into three loose piles on a dark walnut table. The cards carry only faint illegible pencil scribbles. A closed dark grey laptop sits at the top edge of the frame and a matte black ceramic coffee cup at the right. Soft lamp light from the top left with a faint cyan reflection on the table surface, shallow depth of field, quiet focused working mood.


### Hero proof-row headshots

The five proof-row tiles are real-looking headshots of the five customers quoted in the wall, not initials. Same art direction as the portraits above, tighter crop. Prompts:

- `ava-jonas`: Tight head-and-shoulders portrait, face centered and filling most of the square frame with a little space above the hair, looking at the camera with a natural relaxed expression. Seamless dark graphite studio backdrop, soft key light from camera left, faint cyan rim light on one shoulder. The subject is a German man in his early forties with short light brown hair and light stubble, wearing a dark grey crewneck sweater.
- `ava-dev`: Tight head-and-shoulders portrait, face centered and filling most of the square frame with a little space above the hair, looking at the camera with a natural relaxed expression. Seamless dark graphite studio backdrop, soft key light from camera left, faint cyan rim light on one shoulder. The subject is an Indian man in his early thirties with short black hair and a neatly trimmed beard, wearing a navy button-up shirt.
- `ava-elena`: Tight head-and-shoulders portrait, face centered and filling most of the square frame with a little space above the hair, looking at the camera with a natural relaxed expression. Seamless dark graphite studio backdrop, soft key light from camera left, faint cyan rim light on one shoulder. The subject is a woman in her mid thirties with auburn hair tied in a low bun, wearing a soft grey knit sweater.
- `ava-mei`: Tight head-and-shoulders portrait, face centered and filling most of the square frame with a little space above the hair, looking at the camera with a natural relaxed expression. Seamless dark graphite studio backdrop, soft key light from camera left, faint cyan rim light on one shoulder. The subject is an East Asian woman in her late twenties with straight shoulder-length black hair, wearing a black turtleneck.
- `ava-priscilla`: Tight head-and-shoulders portrait, face centered and filling most of the square frame with a little space above the hair, looking at the camera with a natural relaxed expression. Seamless dark graphite studio backdrop, soft key light from camera left, faint cyan rim light on one shoulder. The subject is a Nigerian woman in her mid forties with natural hair pulled back and small gold stud earrings, wearing a charcoal blazer.
