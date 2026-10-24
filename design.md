# Design: PixShare

PixShare is a working photography application. The photographs, captions and
actual controls are its material. Preserve routes, authentication and data flows.

## System

- Genre: editorial; application screens use the same restrained shell.
- Theme: Hallmark Atelier, explicitly selected by the user.
- Palette: Atelier warm paper, umber ink and muted slate; matching warm dark mode. No forest green.
- Shape: a simple online photo album opening directly onto real photographs.
- Signature: full photographic composition, with orderly proportionate rows.
- Tokens: `web/app/globals.css`, `:root` and declared dark overrides are canonical.
- Fonts: Sentient 300/400 for display; Hanken Grotesk 400 for controls and reading.
  Hanken is local/OFL; Sentient uses the official Fontshare API with Georgia fallback.

## Composition

Use the centered 1344px shell and its 48/28/20px responsive gutters. Native-ratio
rows preserve DOM order; images use contain fit and existing responsive sources.
Mobile is a single readable column. Captions stop at two lines in the gallery;
full text belongs on the existing detail page. A sparse final row stays bounded.

Keep navigation to the existing destinations, with native focus and touch
controls. Use a simple colophon. The upload form places the real file picker
beside caption fields on desktop and stacks them in source order on mobile.

## Finish

One heading color and weight, no heading fragments in italics. Labels use the
body face in sentence case without tracking. Thin paper mats around photographs, no photographic color filters. No decorative arrows, status dots,
texture, gradients or moving photographs. A contained photo has no color filter.

Focus is instant and visible. Real loading/error/empty/success states stay wired
to their handlers. Keep reduced-motion support and native dialog behavior. Do
not add marketing metrics, stock social proof, product features or fake content.

## Exports

`web/app/globals.css` owns tokens and primitives. Route files compose the working
components; `Gallery`, `PostCard`, `PostForm` and `PostImage` own their surfaces.
