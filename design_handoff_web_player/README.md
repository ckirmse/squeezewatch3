# Handoff: Whole-House Audio — Web Player

## Overview
A responsive web interface ("Amplr") for controlling a whole-house audio system: now-playing display, transport controls, seek + volume scrubbers, a room selector, room grouping, and a Favorites picker. It shares its visual language with an LVGL device UI for the same system (dark brushed-metal neumorphism, cyan accent).

## About the Design Files
The file in this bundle (`Audio UI Assets for Web.dc.html`) is a **design reference created in HTML** — a working prototype showing the intended look and behavior. It is **not production code to copy directly**. The `.dc.html` format wraps a small custom runtime (`support.js`); ignore that scaffolding.

The task is to **recreate this design in the target codebase's existing environment** (React, Vue, Svelte, etc.) using its established patterns, component library, and state management. If no frontend exists yet, choose the most appropriate framework and implement it there. Treat the HTML as the source of truth for layout, styling, and interaction — not as files to ship.

## Fidelity
**High-fidelity.** Final colors, typography, spacing, shadows, and interactions. Recreate the UI pixel-accurately using the codebase's own libraries. All values below are exact.

## Screens / Views

### Single screen: Player
One responsive page, max content width **1080px**, centered, with page padding `clamp(16px,4vw,44px)` top / `clamp(14px,4vw,40px)` sides / `clamp(40px,7vw,72px)` bottom.

Page background: `#141613` plus two layers — a radial cyan wash `radial-gradient(140% 120% at 20% 0%, rgba(72,196,216,0.06), transparent 55%)` over a tiling texture `bg_texture.png` at `128px 64px`.

Vertical stack, gap `clamp(18px,3.5vw,32px)`:

**1. Header** — flex row, space-between, wraps. Bottom border `1px solid rgba(255,255,255,0.08)`, padding-bottom `clamp(14px,2.5vw,22px)`.
- Left: 38×38 rounded-10 embossed logo tile (`linear-gradient(145deg,#464c54,#23272d)`, shadow `-3px -3px 7px rgba(255,255,255,0.05), 3px 3px 8px rgba(0,0,0,0.6)`) holding a cyan speaker SVG; beside it an eyebrow "WHOLE-HOUSE AUDIO" (Fira Code, 10.5px, letter-spacing 3px, uppercase, `#48c4d8`) over the wordmark "Amplr" (Montserrat 600, `clamp(17px,2.6vw,21px)`, `#eef2f6`).
- Right: a **Favorites** button and the **room dropdown** (see Components).

**2. Player** — flex row, gap `clamp(20px,3.5vw,34px)`, wraps.
- **Album art**: `flex:1 1 300px; max-width:400px`. Square (`aspect-ratio:1/1`) raised bezel, radius 14, padding 14, `linear-gradient(145deg,#3a4048,#20242a)`, shadow `-7px -7px 16px rgba(255,255,255,0.04), 8px 9px 22px rgba(0,0,0,0.6)`. Inside, a recessed well (radius 8, `inset 3px 3px 10px rgba(0,0,0,0.85), inset -2px -2px 6px rgba(255,255,255,0.05)`) shows a placeholder gradient + a spinning "vinyl" disc (animation `spinvinyl 8s linear infinite` while playing) with a cyan center dot. Top-right: a 3-bar equalizer that animates (`eqbar 0.9s ease-in-out infinite`, staggered 0/0.3/0.6s) only while playing.
- **Right column**: `flex:2 1 360px`, vertical stack gap `clamp(16px,2.5vw,22px)`:
  - **Data field** (now-playing): radius 14, padding `clamp(20px,3vw,30px)`, `#181b18` + `bg_texture.png` at 128×64, recessed shadow `inset 3px 3px 9px rgba(0,0,0,0.72), inset -3px -3px 8px rgba(255,255,255,0.05)`. Contents: "NOW PLAYING" eyebrow (Fira Code 10.5px, ls 2.5px, `#48c4d8`); title (Montserrat 500, `clamp(22px,4vw,30px)`, `#eef2f6`); artist·room (Roboto, `clamp(13px,2vw,15px)`, `#8b939c`); then the **seek scrubber**.
  - **Transport row**: centered, gap `clamp(18px,4vw,30px)`. Prev/Next round buttons `clamp(54px,13vw,64px)`; Play/Pause `clamp(76px,20vw,92px)`. See Components for the neumorphic recipe.
  - **Volume row**: speaker icon + volume scrubber + numeric readout (Fira Code 12px, `#6f7883`, right-aligned, width 38px).

**3. "Playing in" section** — heading "Playing in" (Montserrat 600, 15px, `#e4e9ee`) + hint (Fira Code 11px, `#6f7883`), then a wrapping row of **room group chips** (gap 12px).

**Favorites overlay** (see Components) — a modal that slides up from the bottom.

## Components

### Round transport button (neumorphic)
- Circle, `border-radius:50%`, centered SVG glyph.
- **Rest**: `background:linear-gradient(145deg,#464c54,#23272d)`; `box-shadow:-5px -5px 11px rgba(255,255,255,0.05), 5px 6px 14px rgba(0,0,0,0.6), inset 1px 1px 1px rgba(255,255,255,0.07)`.
- **Active/pressed**: `background:linear-gradient(145deg,#22262c,#3a4048)`; `box-shadow:inset 4px 4px 8px rgba(0,0,0,0.6), inset -3px -3px 6px rgba(255,255,255,0.05), 0 0 10px rgba(72,196,216,0.4)`.
- Glyph fill `#aeb6bf` (prev/next), `#eaf7fa` (play/pause). Play button adds a faint cyan ring `0 0 0 1px rgba(72,196,216,0.25)` at rest and stronger inner glow when active.

### Scrubber (seek & volume share one recipe)
- Clickable track wrapper with `padding:8px 0` (enlarges hit area).
- Track: `height:6px; border-radius:3px; background:rgba(0,0,0,0.55); box-shadow:inset 0 1px 3px rgba(0,0,0,0.7)`.
- Fill: `width:<pct>%`, `background:linear-gradient(90deg,#2f9fb0,#48c4d8)`, `box-shadow:0 0 8px rgba(72,196,216,0.55)`.
- Knob: 14×14 circle `#eaf7fa`, centered on the fill edge (`left:<pct>%; transform:translate(-50%,-50%)`), `box-shadow:0 0 9px rgba(72,196,216,0.9), 0 1px 2px rgba(0,0,0,0.5)`.
- Below seek: elapsed (`#48c4d8`) left / total (`#6f7883`) right, Fira Code 12px.
- Click math: `f = clamp((clientX - rectLeft) / rectWidth, 0, 1)`.

### Room dropdown
- Button: min-width 190px, padding `10px 14px`, radius 8, `linear-gradient(180deg,#2a2f35,#1f2328)`, border `1px solid rgba(255,255,255,0.06)`, shadow `0 2px 5px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.05)`; hover `linear-gradient(180deg,#2f353c,#22262c)`. Contains a cyan status dot (8px, glow), the active room name (Montserrat 14px), and a chevron that rotates 180° when open (`transition:transform .18s`).
- Menu: absolute, `top:calc(100% + 8px)`, radius 10, `linear-gradient(180deg,#20242a,#191c21)`, shadow `0 12px 28px rgba(0,0,0,0.6)`, border `1px solid rgba(255,255,255,0.08)`, padding 6. Rows: padding `10px 12px`, radius 6; selected row `background:rgba(72,196,216,0.12)`, text `#eaf7fa`, dot `#48c4d8`; others text `#c8ced6`, dot `rgba(150,160,170,0.4)`; hover `rgba(72,196,216,0.10)`.

### Room group chip
- padding `12px 16px`, radius 10, Montserrat 14px, a 9px status dot, name, and a small meta label (Fira Code 10.5px).
- **On**: bg `linear-gradient(180deg,rgba(72,196,216,0.16),rgba(72,196,216,0.06))`, border `rgba(72,196,216,0.4)`, shadow `0 0 14px rgba(72,196,216,0.18), inset 0 1px 0 rgba(255,255,255,0.06)`, text `#eaf7fa`, dot `#48c4d8` (glow `0 0 8px rgba(72,196,216,0.85)`), meta = volume number in cyan.
- **Off**: bg `linear-gradient(180deg,#23272d,#1c1f24)`, border `rgba(255,255,255,0.06)`, text `#8b939c`, dot `rgba(150,160,170,0.35)`, meta "off" in `#5f6873`.

### Favorites button + overlay
- **Button** (header): padding `10px 15px`, radius 8, same base gradient/border/shadow as the dropdown button, a cyan star SVG + "Favorites" (Montserrat 14px).
- **Overlay**: `position:fixed; inset:0; z-index:50; background:rgba(8,10,12,0.72); backdrop-filter:blur(3px)`; aligns its panel to the bottom-center (`align-items:flex-end`), padding `clamp(0,3vw,40px)`. Click on the backdrop closes; click inside does not (stop propagation).
- **Panel**: `width:100%; max-width:760px; max-height:min(84vh,720px)`, radius `16px 16px 0 0`, `linear-gradient(180deg,#20242a,#171a1e)`, shadow `0 -12px 40px rgba(0,0,0,0.7)`, border `1px solid rgba(255,255,255,0.08)`. Header row: star + "Favorites" (Montserrat 600, `clamp(17px,3vw,20px)`) + "N saved" (Fira Code 11px, `#6f7883`) + a 34×34 close button (rest bg `rgba(255,255,255,0.04)`, `#8a929b`; hover bg `rgba(255,255,255,0.09)`, `#e4e9ee`).
- **List**: scrollable grid, `grid-template-columns:repeat(auto-fill,minmax(200px,1fr))`, gap 12, padding `clamp(14px,2.5vw,20px)`. Each item is a button: padding `14px 15px`, radius 11, a 7px dot + the favorite name (Montserrat 14px, ellipsis-truncated). Currently-playing item: bg `rgba(72,196,216,0.12)`, border `rgba(72,196,216,0.4)`, text `#eaf7fa`, dot `#48c4d8`; others bg `rgba(255,255,255,0.02)`, border `rgba(255,255,255,0.06)`, text `#e4e9ee`, dot `rgba(150,160,170,0.35)`; hover `rgba(72,196,216,0.10)`.

## Interactions & Behavior
- **Play/Pause** toggles playback; swaps play↔pause glyph; starts/stops the vinyl spin and equalizer animation.
- **Prev/Next** load the previous/next track (wrap-around), reset elapsed to 0, keep playing.
- **Seek** — click anywhere on the seek track to jump elapsed to that fraction of total.
- **Volume** — click anywhere on the volume track to set volume 0–1; readout shows 0–100.
- **Playback timer** — while playing, elapsed increments 1s per second; wraps to 0 at the end (a real app would advance to the next track).
- **Room dropdown** — opens/closes on click; selecting sets the active room and closes.
- **Group chips** — toggle a room in/out of the current group.
- **Favorites** — button opens the overlay; selecting a favorite loads it as the current track and starts playback, then closes; backdrop or close button dismisses.
- **Responsive** — pure fluid layout via `clamp()`, `aspect-ratio`, and `flex-wrap` (no media queries). Two columns on wide screens; album art and controls stack into one column when width is tight. Touch targets stay ≥44px on mobile via the `clamp()` minimums.

## State Management
- `playing` (bool)
- `elapsed` (sec), `total` (sec) — current track position/length
- `vol` (0–1)
- `trackIdx` (int) into the track list
- `activeRoom` (string), `roomsOpen` (bool)
- `group` (map room→bool) for whole-house grouping
- `favsOpen` (bool)
- Data fetching: replace the hard-coded track list, room list, and favorites with server data. **Favorites is an array of ~20 plain strings** (names only — no art, no metadata). Selecting one should trigger the real "play favorite" call.

## Design Tokens
**Colors**
- Page bg `#141613`; texture base `#181b18`
- Panel gradients: raised `#464c54→#23272d` (145deg); recessed field `#181b18`; menu `#20242a→#191c21`
- Cyan accent `#48c4d8`; bright cyan `#6fdcec`; deep cyan `#2f9fb0`; near-white cyan `#eaf7fa`
- Text: primary `#eef2f6` / `#e4e9ee`; secondary `#c8ced6` / `#d3d9df`; muted `#8b939c`; dim `#6f7883` / `#5f6873`; glyph `#aeb6bf`
- Hairlines: `rgba(255,255,255,0.06–0.08)`

**Typography**
- Display / titles / labels: **Montserrat** 500/600
- Body / secondary: **Roboto** 400/500
- Numeric, eyebrows, meta: **Fira Code** 400/500 (uppercase eyebrows use letter-spacing 2.5–3px)

**Radius**: 6 (menu rows), 8 (fields/wells/buttons), 10 (menus/chips), 11 (fav items), 14 (cards), 16 (overlay top), 50% (round buttons/knobs/dots).

**Shadows**: raised `-Npx -Npx blur rgba(255,255,255,0.04–0.06), Npx Npx blur rgba(0,0,0,0.6)`; recessed `inset …rgba(0,0,0,0.55–0.85)` + `inset …rgba(255,255,255,0.05)`; cyan glow `0 0 8–16px rgba(72,196,216,0.4–0.9)`.

**Animations**: `spinvinyl` 8s linear infinite (rotate 360°); `eqbar` 0.9s ease-in-out infinite (scaleY 0.35→1→0.5), staggered.

## Assets
- **`bg_texture.png`** — 128×64 seamless dark brushed-metal tile (user-provided). Tiles behind the page and inside the data field. Included in this bundle.
- All icons are **inline SVG** (speaker, star, chevron, close, play/pause/prev/next, equalizer, volume) — no icon font. Recreate with the codebase's icon set or keep as inline SVG.
- Fonts loaded from Google Fonts: Montserrat, Roboto, Fira Code.

Note: the sibling LVGL device kit (`Audio UI Asset Kit.dc.html` + `assets/*.png`) contains baked PNG versions of these same components for the embedded device — not needed for the web build, but useful as a visual cross-reference.

## Files
- `Audio UI Assets for Web.dc.html` — the responsive web player prototype (this handoff's subject).
- `assets/bg_texture.png` — the tiling background texture.
