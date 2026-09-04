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
