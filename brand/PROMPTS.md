# Brand and design prompts

Paste these into Gemini (or any image model). Each is self-contained. `brand/icon.svg` is the current app icon; the
palette below is the wall's own (`coptoc/web/src/index.css`).

Palette: ground `#0b0f14`, panel `#111821`, line `#223041`, text `#dce4ee`, dim `#7b8aa0`, blue force `#3b82f6` /
`#60a5fa`, amber (elevated) `#f59e0b`, red (critical / FLASH) `#ef4444`, green (normal / safe) `#22c55e`,
purple (operations / events) `#c084fc`.

---

## 1. Logo and wordmark

> Design a logo system for **TOC**, an open-source Tactical Operations Center for corporate security teams. It is
> three products under one name: **Coptoc** (the Common Operating Picture — one wall with a map at the center and
> staff-section panels around it), **Sigtoc** (the S2, intelligence: requirements, collection, cases, assessments), and
> **Modtoc** (a content-moderation engine). The author is a former US Army military intelligence officer; the product
> encodes real staff doctrine (S1 personnel, S2 intel, S3 operations, S6 comms), the shift-change brief, roll calls,
> and the FLASH warning. Tone: serious, calm, precise, professional, never militaristic kitsch — no eagles, no
> crosshairs on people, no camouflage, no shields.
>
> The existing app icon is a blue dot (our people) inside an amber ring (a threat's radius) on a near-black map grid
> with four compass ticks. Build the logo from the same idea or from one of these: the map pin as a dot with a radius,
> a hash-chain (every action is on an immutable ledger), the watch (a 24-hour shift ring), concentric rings that read
> as both radar and posture.
>
> Deliver, on a `#0b0f14` background and again on white:
> 1. A primary mark (symbol only), geometric, works at 16 px and at 2 m.
> 2. A wordmark "TOC" in a monospaced or engineered grotesk face, wide letter-spacing, with the expansion
>    "TACTICAL OPERATIONS CENTER" set small beneath it in the same face.
> 3. A lockup: mark left, wordmark right.
> 4. Three sub-brand lockups sharing the mark with one accent each: **COPTOC** in blue `#3b82f6`, **SIGTOC** in amber
>    `#f59e0b`, **MODTOC** in purple `#c084fc`.
> 5. A one-color version of the mark in `#dce4ee`.
>
> Style references: Teenage Engineering product labels, NASA JPL mission patches reduced to two colors, Bloomberg
> Terminal's discipline without its clutter, the type on a Casio G-Shock face. Flat vector, no gradients except a
> single soft glow behind the blue dot, no 3D, no bevels, no mockups on hats. Show all five items on one sheet, each
> labeled, with generous spacing.

Variant to try second: replace the mark brief with "a single amber ring broken at 12 o'clock by a small blue dot,
like a watch hand at the start of a shift".

---

## 2. UI mockups — the same information, less text

Attach a screenshot of the current wall (`docs/wall.png`, or take one from http://localhost:5173) with the prompt.

> This is the current interface of **TOC**, a security operations center wall. It works, but it is dense and
> text-heavy, like a Bloomberg terminal. Redesign it to carry the same information with less reading: more shape,
> color, position, and motion; fewer labels and numbers on screen at once; the same discipline. Keep the dark palette
> (ground `#0b0f14`, panels `#111821`, text `#dce4ee`, blue `#3b82f6` for our people, amber `#f59e0b` for elevated,
> red `#ef4444` for critical and FLASH, green `#22c55e` for normal and safe, purple `#c084fc` for operations).
>
> The wall must show, at a glance, for a watch officer on a 12-hour shift:
> - The map at the center: our sites (posture colored), travelers, events, threat rings by severity, travel routes.
> - Top strip: the overall posture, who holds the watch and when it ends, and a few counts (people, traveling,
>   VIPs out, threats, confirmed, unaccounted). A red FLASH bar when a warning is released.
> - Left, S1 personnel: sites with present/assigned, travelers with check-in freshness, open roll calls with progress.
> - Right, S2 intelligence: warnings awaiting release, requirements with coverage bars and gaps, threats, assessments
>   with likelihood + confidence, cases with a review count, the daily INTSUM headline.
> - Bottom, S3 operations: upcoming events and trips as cards with coverage and operation progress, and the battle log
>   (a live, hash-chained record of every action).
> - Overlays for detail: a site, a person, a threat, an event, a roll-call roster with call buttons, the shift-change
>   brief, the area assessment matrix (candidates × indicators, cells reported / quiet / not collected), the INTSUM.
>
> Design rules to respect: nothing is scored or ranked by the machine — humans confirm and approve, so every
> "suggested" thing must look visibly provisional next to "confirmed" things. Severity and posture are the two color
> systems; do not add a third. Numbers only where they change a decision. Every action must remain one tap from the
> map. It must work on a 1920×1080 wall display, a laptop, a phone in landscape, and a phone in portrait.
>
> Give me four directions as full-screen desktop mockups, each with a short rationale:
> A. **Map-first**: the map is 80% of the screen; panels become thin edge rails that expand on hover.
> B. **Radial**: the wall as concentric rings around the map — inner ring people, middle ring threats, outer ring
>    time (the shift, the next 90 days).
> C. **Cards and tiles**: a Linear/Vercel-style dark dashboard with card stacks, big posture tile, sparse mono labels.
> D. **Timeline-led**: a horizontal time axis across the top (the shift, then the next 90 days) with everything hung
>    from it; the map below.
>
> For the best direction also show: the phone portrait version, the roll-call overlay, and the FLASH state. Use real
> content, not lorem ipsum: sites like "San Francisco HQ", travelers like "Alex Ventura — Riyadh", a threat like
> "Transport strike called — Lisbon metro", an INTSUM headline like "5 new threats, worst elevated; 1 organic report;
> 1 open collection gap." Flat, crisp, no glassmorphism, no neon, no 3D.

Variant to try second: "Do the minimalist extreme: what is the least this wall can show and still let the watch
officer act within five seconds of a FLASH? Then show how the rest reveals on demand."

---

## 3. App icon

> Design an iOS and Android app icon for **TOC**, an open-source Tactical Operations Center for corporate security
> teams — the wall a watch officer runs a 12-hour shift from: one map at the center, the staff sections around it,
> ops and intelligence feeding each other. The author ran one of these rooms in Iraq as the intelligence officer.
>
> I want one idea, drawn once, that a person remembers after seeing it a single time on a home screen. Not a dot in a
> ring, not a generic map pin, not a shield, not crosshairs, not radar, not an eagle, not a globe. One bold shape,
> two colors at most on a dark ground, no text unless the letterform *is* the idea.
>
> Explore these four ideas and pick the strongest:
> 1. **Fusion.** Two rings, blue (our people, operations) and amber (intelligence, the outside world), overlapping;
>    the overlap is the brightest thing on the icon. That overlap is what a TOC is.
> 2. **The wall.** A dark square divided into a coarse grid of panels with the center cell lit like a map — the room
>    itself, seen from the watch officer's chair.
> 3. **Shift change.** A thick ring with one clean break at twelve o'clock: the 24-hour watch, the moment the brief
>    is handed over.
> 4. **The letter.** A "T" built from a horizontal bar and a vertical stroke that read as a wall and its floor, or as
>    an antenna mast; monospaced, heavy, slightly extended, with one amber accent.
>
> Palette: ground `#0b0f14`, blue `#3b82f6`, amber `#f59e0b`, off-white `#dce4ee`. Flat vector, hard edges, one soft
> glow allowed, no gradients on the ground, no 3D, no bevels, no gloss. It must survive at 29 px and at 1024 px, in
> the iOS rounded mask and inside an Android circle, and still be recognizable in monochrome.
>
> Show each idea as a 1024×1024 icon on a phone home screen next to Mail, Maps, and Slack so I can judge it in
> company, then show the winner alone, large, with a two-sentence reason it will be remembered.

Variant: "Same brief, but the icon must work as a single-color stamp on a black hoodie and as a 16 px favicon.
Kill every idea that does not survive both."

---

## 3b. App icon, second brief — no circles

> Design an app icon for **TOC**, an open-source Tactical Operations Center for corporate security: the wall a watch
> officer runs a 12-hour shift from. Hard rule: **no circles, no rings, no compass, no pins, no radar, no globes, no
> crosshairs, no shields, no eagles**. Every company already has the ring-with-a-dot; I do not want it. Rectilinear
> geometry only — bars, blocks, grids, chevrons, letterforms. One idea, bold enough to be drawn from memory.
>
> Four ideas, each rooted in something the product does:
> 1. **The wall.** A dark square split into a coarse grid of panels, like a control room seen head-on from the
>    officer's chair: most panels near-black, one wide center panel a deep blue block (the map), one small panel
>    amber (an alert). Think Mondrian at night, or a server-rack face. No text.
> 2. **Shift change.** Two heavy horizontal bars stacked, one blue and one amber, the top one offset a step to the
>    right: the outgoing watch handing to the incoming. Or two interlocking rectangular hooks in those colors.
> 3. **Accountability.** A 3×3 field of squares, all off-white, one amber: a roll call with one name unaccounted for.
>    The single odd square is the whole story.
> 4. **The monogram.** A heavy "T" whose crossbar is a wide slab (the wall) and whose stem is a narrow stroke (the
>    floor beneath it), in an extended monospaced grotesk, off-white on the dark ground, with a single amber tick at
>    the right end of the crossbar. Letterform icons are remembered (Notion, Threads, Linear).
>
> Palette: ground `#0b0f14`, blue `#3b82f6`, amber `#f59e0b`, off-white `#dce4ee`. Flat, hard-edged vector, no
> gradients, no glow, no 3D, no bevel, no gloss, no text other than idea 4. Must survive at 29 px and at 1024 px,
> inside the iOS rounded mask and inside an Android circle, and read in one color.
>
> Show each idea at 1024×1024 on a phone home screen beside Mail, Maps, and Slack, then the winner alone, large,
> with a two-sentence reason a stranger would recognize it a week later.

---

## 4. Google Stitch — UI directions

Stitch builds one screen per prompt. Start with the main prompt, then paste the follow-ups one at a time to branch.
Attach `docs/wall.png` as the reference if it asks for one, and say "do not copy the layout".

### Main prompt — the wall, map-first

> A dark, minimalist security operations dashboard for desktop (1920×1080) called TOC. The interface is a full-bleed
> world map (dark basemap, near-black land, slightly lighter water lines) that fills the entire screen. Everything
> else floats over the map as thin, translucent panels with 1 px borders; no solid sidebars, no dense tables.
>
> Top edge, one slim bar, left to right: the wordmark "TOC" in a monospaced font; a posture pill reading "ELEVATED"
> in amber; a watch pill reading "DUBLIN WATCH · R. Kovac · 5h12 left"; then six large numerals with tiny mono
> labels beneath: 97 PERSONNEL, 5 TRAVELING, 4 VIP OUT, 7 THREATS, 3 CONFIRMED, 0 UNACCOUNTED; a role selector at
> the far right reading "Battle Captain". Directly under the bar, a red strip that appears only when a warning is
> live: a pulsing red "FLASH" tag, the text "Online threats against data center operators — DC-East (Virginia)",
> and one green "ACKNOWLEDGE" button.
>
> On the map: our sites as small solid dots colored by posture (green normal, amber elevated, red critical) with a
> short label; travelers as blue dots with a first name; events as purple diamonds; threats as translucent amber or
> red rings sized by radius; travel routes as thin blue arcs. Clusters when zoomed out show a count.
>
> Left edge: a narrow vertical rail of icons for S1 Personnel, S2 Intelligence, S3 Operations, S6 Roll calls, and the
> Battle log. Hovering or clicking a rail icon slides out a 320 px panel over the map. Show the S1 panel open: a list
> of eight sites, each row a posture dot, the site name, and "34/39" present/assigned in mono; below it "TRAVELING 5"
> with five names, VIPs starred, each with a small green "✓ 2h" check-in chip.
>
> Right edge: the S2 panel open, 340 px: a "WARNINGS · 1 awaiting release" header with one card (a red CRITICAL chip,
> the title "Credible threat to venue — LVMPD advisory", buttons "RELEASE · SMS + CHAT" and "CANCEL"); then
> "REQUIREMENTS · 44 active · 92% coverage" with rows of "P1 TRIP  Priya Ramanathan — London Office  7/8" over a
> thin amber progress bar; then "THREATS · 7 · 5 live" with rows of a severity chip and a title.
>
> Bottom edge: a single horizontal strip of cards over the map, scrolling sideways: event cards ("T-21d ★ EMEA
> Engineering Summit · London Office · 6 attending · COVER 2/3") and trip cards ("ACTIVE ★ Alex Ventura · San
> Francisco → Riyadh · OP 2/4"). To its right, a compact battle log: five one-line entries, each a mono timestamp,
> a small blue or amber type tag, and a sentence.
>
> Typography: an engineered grotesk for content, a monospace for labels, numerals, and timestamps; labels are 9–10 px
> uppercase with wide tracking; nothing bold except numerals and titles. Colors: ground #0b0f14, panels #111821 at
> 92% opacity, lines #223041, text #dce4ee, dim #7b8aa0, blue #3b82f6, amber #f59e0b, red #ef4444, green #22c55e,
> purple #c084fc. Flat, crisp, no glassmorphism blur, no neon, no drop shadows heavier than 1 px lines. Sparse:
> generous padding, at most one number per row, color and position carrying meaning instead of text.

### Follow-ups, one at a time

1. "Collapse both side panels to their rails so the map fills 90% of the screen. Show what the rail icons look like
   with small badge counts (S2 shows 1 for the pending warning, S6 shows 0)."
2. "Add a roll-call overlay: a 420 px panel over the map titled 'Roll call — London Office · 9/15 accounted', a
   thick progress bar, chips 'UNREACHABLE 2 · ASSIST 1 · UNACCOUNTED 3 · SAFE 9', a green button 'REQUEST CHECK-INS ·
   SMS + CHAT (5)', then a roster list sorted unreachable first, each row a name, phone in mono, and four small
   buttons SAFE, NO ANSWER, ASSIST, INJURED. One row carries a red 'AUTO · 15m' chip."
3. "Show the same wall on a phone in portrait (390×844): the map fills the screen, the top bar collapses to the
   posture pill and the watch, the FLASH strip stays, and the four sections become a bottom tab bar (COP, S1, S2,
   S3). Show the S2 tab open as a full-screen list."
4. "Redesign the top bar as a single horizontal timeline instead of counters: the current 12-hour watch as a bar with
   a marker at 'now', the handover at the right end, events and trip departures for the next 90 days plotted to its
   right at a compressed scale. Keep everything else."
5. "Make the version that Linear or Vercel would ship: cards with 8 px radius, a big posture tile top-left, ultra-
   sparse mono labels, more empty space, the map reduced to a 60% wide tile in the center."
6. "Show the FLASH state at full intensity: the released warning, the whole top bar tinted, the affected site
   pulsing on the map, the roll-call button surfaced next to the warning."
7. "Show the area assessment overlay: a matrix with two columns 'Lisbon, Portugal' and 'Porto, Portugal' and nine
   rows of indicators; cells read 'unlikely · 20–45% · low conf' in amber, 'quiet · GDACS watching' in green, or
   'not collected → USGS' in red; no scores, no totals, a BLUF paragraph per column beneath."
