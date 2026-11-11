---
name: odoo-module-index-html
description: >
  Guide for creating a professional static/description/index.html for any Odoo module.
  Covers the standard section layout (hero banner, feature highlights, demo screenshots,
  syntax showcase, comparison table, how-it-works steps, technical specs, support footer),
  asset organization (banner.png, icon.png, assets/ folder), manifest image declaration,
  and writing conventions (English only, inline CSS, Odoo Bootstrap classes, Font Awesome icons).
  Use whenever a module needs a new or improved App Store / module info page.
globs: "**/static/description/index.html"
license: MIT
author: Dat Nguyen
version: 1.0.0
---

# Odoo Module `index.html` — Creation Guide

Every Odoo module should have a polished `static/description/index.html` that displays in the
Odoo App Store and in the module's info page inside the backend. This skill guides you through
creating one from scratch, maintaining the same look and feel as the reference example.

> **Reference implementation**: the `index.html` in this skill folder was built for
> `dn_excel_template_report`. Use it as the visual and structural template.

---

## File & Asset Layout

```
<module>/
└── static/
    └── description/
        ├── index.html          ← the page you are building
        ├── banner.png          ← wide hero image (1200×300 px recommended)
        ├── icon.png            ← square module icon (256×256 px)
        └── assets/             ← demo screenshots referenced inside index.html
            ├── screenshot1.jpg
            ├── screenshot2.jpg
            └── ...
```

Images inside `index.html` are referenced with **relative paths**:
```html
<img src="assets/screenshot1.jpg" ...>
<img src="banner.png" ...>
```

---

## Manifest: Declare the Banner

The `images` key in `__manifest__.py` tells Odoo which image to show as the module thumbnail
in the App Store. It **must** point to `banner.png`:

```python
{
    'name': 'My Module',
    'images': ['static/description/banner.png'],
    ...
}
```

If the `images` key is missing, **add it**. If `banner.png` does not exist yet, create or
export one (see Asset Guidelines below).

---

## Page Structure (8 Standard Sections)

Build the page in this order. Each section uses the CSS class `oe_container` which Odoo's
backend wraps in a responsive container.

```
1. HERO BANNER          Light card with title, subtitle, tag pills, right panel
2. WORKFLOW OPTIONS     Two-column cards (e.g. No-Code vs Python-Code modes)
3. DEMO SCREENSHOTS     Full-width images with captions that show real UI
4. VALUE HIGHLIGHTS     3-column benefit cards (icon + heading + paragraph)
5. SYNTAX / FEATURES    Code blocks or feature detail panels
6. COMPARISON TABLE     Module vs alternatives (plain HTML table)
7. HOW IT WORKS         Numbered step cards (Step 1 → Step 4)
8. TECH SPECS           Two-column spec list + support/author footer
```

Not all sections are mandatory — include only what is relevant to the module.

---

## Odoo Store Sanitizer Compatibility Rules

When Odoo renders `index.html` on the official Odoo App Store and inside the backend Apps view, the HTML is parsed and sanitized by `odoo.tools.mail.html_sanitize`. The underlying sanitizer applies an aggressive style whitelist (`_style_whitelist` in `odoo/tools/mail.py` / `lxml` cleaner):
- The shorthand property `background:` (especially with `linear-gradient(...)` or `url(...)`) is **completely stripped** by the sanitizer! If you rely on a dark background gradient, the background disappears and turns into transparent/white, rendering white text completely invisible (white text on white background)!
- `box-shadow` is **completely stripped**. Cards relying solely on shadows lose their visual separation.
- `gap` (flexbox gap) is **completely stripped**. Flex items will collapse together without spacing.
- `backdrop-filter` is **completely stripped**.

### Golden Rules for 100% Sanitizer Compatibility

1. **100% use `background-color:` instead of `background:`**: Always specify explicit background colors using `background-color: #f8fafc;` or `background-color: #ffffff;`. Never use shorthand `background:`.
2. **Never use gradients on containers containing text**: Gradients are stripped, leaving light text on a transparent or white background.
3. **Never rely on `box-shadow` for card separation**: Always use clean, visible borders such as `border: 1px solid #cbd5e1;` or `border: 1px solid #e2e8f0;`.
4. **Never use inline `gap:`**: Use `margin-right` / `margin-bottom` on child elements (with `display: inline-block;` or `display: inline-flex;`) instead of `gap:` on the parent container.
5. **Dark Palette for all typography**:
   - Primary Headings (H1, H2): `#0f172a` or `#111827`
   - Secondary Headings / Subtitles (H3, H4): `#1e293b`
   - Body & Paragraphs: `#334155` or `#475569`
   - Never use white (`#ffffff`) or light gray (`#cbd5e1`, `#94a3b8`) for text on main page containers.

---

## Writing Rules

| Rule | Detail |
|------|--------|
| **Language** | English only — no Vietnamese inside `index.html` |
| **Styling** | Inline CSS only — no `<style>` tags, no external CSS files |
| **Framework** | Odoo ships Bootstrap 4 — use `col-12`, `col-lg-6`, `row`, `g-4`, `mb-5` etc. |
| **Icons** | Font Awesome 4 is available: `<i class="fa fa-check-circle">` |
| **Images** | Always include `alt` text, `width:100%`, `height:auto` |
| **No JS** | Do not add `<script>` tags — the backend strips them |
| **Colors** | Use the Odoo teal palette: `#017e84` (primary), `#0f172a` (dark text), `#334155` (body text), `#f8fafc` (card light bg) |

---

## Section 1 — Hero Banner

Light card with the module name, one-liner subtitle, feature pills on the left,
and a small info panel on the right.

```html
<section class="oe_container" style="font-family:'Montserrat','Segoe UI',Roboto,sans-serif;">
    <div class="row align-items-center" style="background-color:#f8fafc; border:1px solid #cbd5e1;
         border-radius:20px; padding:48px 36px; margin:0 0 32px 0;">

        <!-- Left: title + description + pills -->
        <div class="col-12 col-lg-8" style="padding-right:24px;">
            <!-- Badge -->
            <div style="display:inline-flex; align-items:center;
                 background-color:#f0fdfa; border:1px solid #017e84;
                 border-radius:9999px; padding:6px 16px; margin-bottom:20px;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color:#017e84; margin-right:8px;"></span>
                <span style="color:#017e84; font-size:12px; font-weight:700; letter-spacing:0.8px; text-transform:uppercase;">
                    Odoo 19 Ready &bull; Community &amp; Enterprise
                </span>
            </div>

            <h1 style="color:#0f172a; font-size:34px; font-weight:800; line-height:1.25; margin:0 0 16px;">
                Module Name
                <span style="display:block; font-size:20px; font-weight:400; color:#334155; margin-top:6px;">
                    One-line subtitle
                </span>
            </h1>

            <p style="color:#334155; font-size:16px; line-height:1.65; margin:0 0 24px;">
                Short description of what the module does.
            </p>

            <!-- Feature pills -->
            <div style="margin-bottom:12px;">
                <span style="display:inline-block; background-color:#ffffff; border:1px solid #cbd5e1;
                      color:#1e293b; padding:6px 14px; border-radius:8px; font-size:12px; font-weight:600;
                      margin-right:8px; margin-bottom:8px;">
                    <i class="fa fa-cubes" style="color:#017e84; margin-right:6px;"></i>Feature A
                </span>
                <!-- repeat for each key feature -->
            </div>
        </div>

        <!-- Right: summary panel -->
        <div class="col-12 col-lg-4 text-center mt-4 mt-lg-0">
            <div style="background-color:#ffffff; border:1px solid #cbd5e1;
                 border-radius:16px; padding:24px;">
                <i class="fa fa-file-excel-o" style="font-size:72px; color:#017e84; margin-bottom:16px; display:inline-block;"></i>
                <h4 style="color:#0f172a; font-size:18px; font-weight:700; margin-bottom:8px;">Key Concept</h4>
                <p style="color:#334155; font-size:13px; line-height:1.5; margin:0 0 16px;">
                    Brief supporting text.
                </p>
            </div>
        </div>
    </div>
</section>
```

---

## Section 3 — Demo Screenshots

Always include **at least one real screenshot**. Use the two-column layout (image left,
caption right) for the first screenshot, then full-width for subsequent ones.

```html
<section class="oe_container mb-5" style="font-family:'Montserrat','Segoe UI',Roboto,sans-serif;">
    <div class="row align-items-center g-4">
        <div class="col-12 col-lg-7">
            <img src="assets/screenshot1.jpg"
                 alt="Description of what is shown"
                 style="display:block;width:100%;height:auto;
                        border:1px solid #cbd5e1;border-radius:12px;">
        </div>
        <div class="col-12 col-lg-5">
            <h2 style="color:#0f172a;font-size:26px;font-weight:800;margin:0 0 12px;">
                What this screenshot shows
            </h2>
            <p style="color:#475569;font-size:15px;line-height:1.7;margin:0;">
                Explain what the user is seeing and why it matters.
            </p>
        </div>
    </div>
</section>
```

---

## Section 4 — Value Highlight Cards (3-column)

```html
<section class="oe_container mb-5" style="font-family:'Montserrat','Segoe UI',Roboto,sans-serif;">
    <div class="row g-4">
        <div class="col-12 col-md-4">
            <div style="background-color:#ffffff;border:1px solid #e2e8f0;border-radius:16px;
                 padding:28px 24px;height:100%;">
                <div style="width:52px;height:52px;background-color:#ecfdf5;border-radius:12px;
                     display:flex;align-items:center;justify-content:center;margin-bottom:20px;">
                    <i class="fa fa-paint-brush" style="font-size:24px;color:#10b981;"></i>
                </div>
                <h3 style="color:#1e293b;font-size:18px;font-weight:700;margin-bottom:12px;">
                    Benefit Title
                </h3>
                <p style="color:#334155;font-size:14px;line-height:1.6;margin:0;">
                    Two to three sentences explaining this benefit clearly.
                </p>
            </div>
        </div>
        <!-- repeat col-12 col-md-4 blocks -->
    </div>
</section>
```

---

## Asset Guidelines

| Asset | Size | Notes |
|-------|------|-------|
| `banner.png` | 1200 × 300 px | Wide landscape; used as App Store thumbnail |
| `icon.png` | 256 × 256 px | Square; transparent background preferred |
| `assets/*.jpg` | 1280–1920 px wide | JPEG quality 85–90; keep under 300 KB each |

---

## Checklist Before Committing

- [ ] `__manifest__.py` has `'images': ['static/description/banner.png']`
- [ ] `banner.png` and `icon.png` exist in `static/description/`
- [ ] All `<img src="assets/...">` files exist in `static/description/assets/`
- [ ] At least one real demo screenshot is included
- [ ] All text is in English
- [ ] No `<script>` tags, no `<style>` blocks
- [ ] Page renders without broken images when opened as a local HTML file

### Sanitizer Compatibility Checklist
- [ ] 100% using `background-color:`, 0 occurrences of shorthand `background:`
- [ ] 0 occurrences of `linear-gradient`
- [ ] 0 occurrences of `box-shadow`, `gap`, `backdrop-filter`
- [ ] All text uses dark typography colors (`#0f172a`, `#1e293b`, `#334155`, `#475569`), no white or light gray text on light containers
