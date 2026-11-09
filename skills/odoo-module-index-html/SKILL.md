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
1. HERO BANNER          Dark gradient card with title, subtitle, tag pills, right panel
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

## Writing Rules

| Rule | Detail |
|------|--------|
| **Language** | English only — no Vietnamese inside `index.html` |
| **Styling** | Inline CSS only — no `<style>` tags, no external CSS files |
| **Framework** | Odoo ships Bootstrap 4 — use `col-12`, `col-lg-6`, `row`, `g-4`, `mb-5` etc. |
| **Icons** | Font Awesome 4 is available: `<i class="fa fa-check-circle">` |
| **Images** | Always include `alt` text, `width:100%`, `height:auto` |
| **No JS** | Do not add `<script>` tags — the backend strips them |
| **Colors** | Use the Odoo teal palette: `#017e84` (primary), `#0f172a` (dark), `#f8fafc` (light) |

---

## Section 1 — Hero Banner

Dark gradient card with the module name, one-liner subtitle, feature pills on the left,
and a small info panel on the right.

```html
<section class="oe_container" style="font-family:'Montserrat','Segoe UI',Roboto,sans-serif;">
    <div class="row align-items-center" style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
         border-radius:20px; padding:48px 36px; margin:0 0 32px 0;">

        <!-- Left: title + description + pills -->
        <div class="col-12 col-lg-8" style="padding-right:24px;">
            <!-- Badge -->
            <div style="display:inline-flex; align-items:center; gap:8px;
                 background:rgba(1,126,132,.2); border:1px solid rgba(1,126,132,.5);
                 border-radius:9999px; padding:6px 16px; margin-bottom:20px;">
                <span style="width:8px;height:8px;border-radius:50%;background:#00d2d3;"></span>
                <span style="color:#5eead4;font-size:12px;font-weight:700;text-transform:uppercase;">
                    Odoo 19 Ready &bull; Community &amp; Enterprise
                </span>
            </div>

            <h1 style="color:#fff;font-size:34px;font-weight:800;margin:0 0 16px;">
                Module Name
                <span style="display:block;font-size:20px;font-weight:400;color:#94a3b8;margin-top:6px;">
                    One-line subtitle
                </span>
            </h1>

            <p style="color:#cbd5e1;font-size:16px;line-height:1.65;margin:0 0 24px;">
                Short description of what the module does.
            </p>

            <!-- Feature pills -->
            <div style="display:flex;flex-wrap:wrap;gap:10px;">
                <span style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);
                      color:#f8fafc;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;">
                    <i class="fa fa-cubes" style="color:#38bdf8;margin-right:6px;"></i>Feature A
                </span>
                <!-- repeat for each key feature -->
            </div>
        </div>

        <!-- Right: summary panel -->
        <div class="col-12 col-lg-4 text-center mt-4 mt-lg-0">
            <div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
                 border-radius:16px;padding:24px;">
                <i class="fa fa-file-excel-o" style="font-size:72px;color:#10b981;margin-bottom:16px;"></i>
                <h4 style="color:#fff;font-size:18px;font-weight:700;margin-bottom:8px;">Key Concept</h4>
                <p style="color:#94a3b8;font-size:13px;line-height:1.5;margin:0 0 16px;">
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
                        border:1px solid #cbd5e1;border-radius:12px;
                        box-shadow:0 8px 20px rgba(15,23,42,.12);">
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
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
                 padding:28px 24px;height:100%;box-shadow:0 4px 6px -1px rgba(0,0,0,.05);">
                <div style="width:52px;height:52px;background:#ecfdf5;border-radius:12px;
                     display:flex;align-items:center;justify-content:center;margin-bottom:20px;">
                    <i class="fa fa-paint-brush" style="font-size:24px;color:#10b981;"></i>
                </div>
                <h3 style="color:#1e293b;font-size:18px;font-weight:700;margin-bottom:12px;">
                    Benefit Title
                </h3>
                <p style="color:#64748b;font-size:14px;line-height:1.6;margin:0;">
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
