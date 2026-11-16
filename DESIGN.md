---
name: Downtify
description: The Printing Desk — a flat, ruled workspace for a self-hosted music library
colors:
  signal-blue: "#0047FF"
  signal-blue-dark: "#4D7AFF"
  newsprint: "#F3F3F0"
  printers-ink: "#171717"
  paper-surface: "#F8F8F6"
  rule: "#232323"
  invert-block: "#1D1D1D"
  on-invert: "#F8F8F6"
  charcoal: "#0C0C0B"
  inverted-ink: "#EDEDEA"
typography:
  display:
    fontFamily: "Space Grotesk Variable, Space Grotesk, Segoe UI, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Inter Variable, Inter, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter Tight Variable, Inter Tight, Inter Variable, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.06em"
  mono:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  none: "0px"
spacing:
  hairline: "2px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.invert-block}"
    textColor: "{colors.on-invert}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.printers-ink}"
    textColor: "{colors.on-invert}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  button-secondary:
    backgroundColor: "{colors.paper-surface}"
    textColor: "{colors.printers-ink}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  icon-button:
    backgroundColor: "transparent"
    textColor: "{colors.printers-ink}"
    rounded: "{rounded.none}"
    size: "40px"
  input-frame:
    backgroundColor: "{colors.newsprint}"
    textColor: "{colors.printers-ink}"
    rounded: "{rounded.none}"
    padding: "12px"
  panel:
    backgroundColor: "{colors.paper-surface}"
    textColor: "{colors.printers-ink}"
    rounded: "{rounded.none}"
    padding: "20px"
  chip-selected:
    backgroundColor: "{colors.invert-block}"
    textColor: "{colors.on-invert}"
    rounded: "{rounded.none}"
    padding: "4px 12px"
---

# Design System: Downtify

## Overview

**Creative North Star: "The Printing Desk"**

A controlled workspace built like a printed technical gazette: warm paper, hard ink, a 2px rule and one blue signal. Every corner is square. Every surface is flat. The interface is read before it is admired.

Density is deliberate. The same table, rule and block vocabulary runs from the 48px masthead to the 64px transport bar, across twenty views. State is shown by inversion or by the single accent — never by decoration. Full-colour covers are the only spontaneous colour in the system; they are content, not chrome.

Motion is diagnostic, not decorative: 80–120ms linear fades, a stepped equalizer, a shimmer with six steps. Nothing springs, floats or glows.

**Key Characteristics:**

- Square geometry: 0 radius on every control, cover and panel.
- 2px structural rules; 1px dividers only inside dense tables.
- One accent, reserved for state: signal blue.
- Flat surfaces; depth through rule, inversion and whitespace.
- Light is default; dark is a full paper/ink inversion.
- Turkish-first, eight locales; labels are short and apparatus-like.

## Colors

Normative values live in the frontmatter; the names below refer to those tokens.

### Primary

- **Signal Blue**: the only accent. Marks the playhead, focus, selection and active state. Its rarity is the point.

### Neutral

- **Newsprint**: the page. A warm light grey, never pure white — pure white beside near-black reads as a light box, not paper.
- **Printer's Ink**: body text and structural rules. Off-black so the 2px rules stay structural without vibrating.
- **Paper Surface**: raised cards and panels, a step above the page.
- **Rule**: the 2px structural line; tables use a lighter divider inside.
- **Invert Block / On Invert**: the solid black block used for primary buttons, active tabs, chips and modal headers.
- **Charcoal / Inverted Ink**: the dark theme. Charcoal, not black, so white text does not halo.

### Named Rules

**The One Voice Rule.** Signal Blue is used for state only, never for decoration or brand display. Keep it under roughly a tenth of any screen.

**The Full Inversion Rule.** Dark mode swaps paper and ink; it does not tint the same surfaces. Source badges become monochrome in both themes — colour comes from artwork only.

## Typography

**Display Font:** Space Grotesk
**Body Font:** Inter
**Label Font:** Inter Tight
**Mono Font:** JetBrains Mono

**Character:** A technical type set: geometric display, neutral body, tight apparatus labels, and a monospace reserved strictly for hashes, bitrate, paths and timestamps. No serif, no italics, no decorative face.

### Hierarchy

- **Display** (bold, clamp 20–32px, tight tracking): titles and now-playing track name.
- **Headline** (bold, Space Grotesk): section and panel headings.
- **Body** (400, 14px): tables, forms, descriptions; no decorative line length rule beyond readability.
- **Label** (600, 11px, uppercase, 0.06em): eyebrows, buttons, tabs, chips — small apparatus type.
- **Mono** (11px, no ligatures): technical values only.

### Named Rules

**The Apparatus Label Rule.** Every button, tab and chip speaks in uppercase 11–12px Inter Tight. Size classes change the block's height and padding, never the voice.

## Layout

Desktop uses a 48px masthead plus a 40px section strip, a fixed 64px transport bar and a 24-block segmented progress meter. Mobile collapses to a 44px header and a full-height block menu with a 56px transport. Panels are two-pane: a 44px section list beside a nine-column configuration panel, separated by a 2px divider.

Spacing follows the ruled grid: 2px hairline gaps between strip cells, 8–12px between controls, 16px between groups, 24px panel padding. Breakpoints are the shipped xs 400px, sm 640px, md 768px, lg 1024px and xl 1280px. Tables stay dense and keyboard-first; nothing floats above its section except modals and toasts.

## Elevation & Depth

The system is flat by doctrine. Shadows, blur, glow and frosted surfaces are absent; the legacy shadow tokens resolve to a transparent offset. Depth is conveyed by the 2px structural rule, inverted blocks and whitespace alone.

### Named Rules

**The Flat Rule.** No shadow, no blur, no glow — if a surface needs to separate, give it a rule or invert it.

## Shapes

Every corner is square. Switches are 24px squares, not pills; progress is 24 separate rectangles, not a rounded track; badges and source labels are monochrome outlined blocks. Structural borders are 2px, inner dividers 1px. There are no circles, no clipped corners and no decorative silhouettes.

### Named Rules

**The Square Rule.** Radius is always 0. The `round` prop on icon buttons exists only for compatibility; it has no visual effect.

## Components

### Buttons

Square blocks, 2px border, uppercase apparatus label. Primary is an invert block; secondary is transparent or paper with a rule; ghost and plain variants drop the border. Hover shifts one tone in 100ms linear; active inverts back. No lift, no scale, no shadow.

### Icon Buttons

Square 32/40/44px cells with a 2px border. The active toggle inverts to the solid block. Keyboard focus is a hard 2px accent rectangle with a 1px offset.

### Inputs and Fields

A 2px frame around a paper-filled 44px block. Focus changes the frame to signal blue; error changes it to danger. Labels are eyebrows above the field, hints and errors are 11px below. No rounded corners, no inner shadow.

### Switch

A 24px square: off is an empty 2px frame, on is an inverted block with an accent tick. No sliding, no transform.

### Progress

Twenty-four equal rectangles, 2px apart. Completed blocks are ink, the block at the playhead is signal blue, the rest are empty frames. A 100ms linear colour change is the only motion.

### Chips and Tabs

Rows of square cells separated by hairline gaps or 1px dividers. The selected cell inverts; unselected cells are outlined and muted. No underline indicator, no movement.

### Panels, Modals and Toasts

Panels are 2px-ruled blocks with a paper surface and inverted header. Modals are square, full-width on phones, with a focus trap. Toasts are hard blocks with a 4px accent leading rule, stacked above modals.

## Do's and Don'ts

### Do:

- **Do** use exactly one accent, signal blue, and only for state, focus and playhead.
- **Do** keep every corner at 0px radius and every structural border at 2px.
- **Do** use inversion — not a tint — to express selection and activation.
- **Do** keep motion at 80–120ms linear, and only where it reports state.
- **Do** keep type in the four shipped families, with mono reserved for technical data.

### Don't:

- **Don't** add shadows, blur, glow, gradients or frosted glass; the tokens are transparent by design.
- **Don't** introduce a second accent or colour-code a source badge; colour belongs to artwork.
- **Don't** round a control, a cover or a panel — even slightly.
- **Don't** animate a button with scale, lift or a spring; the interface reports, it does not perform.
- **Don't** claim an accessibility standard that has not been agreed; preserve the eight locales, both themes and keyboard reach instead.
