---
name: module-standards
description: >-
  Standards for dn_* Odoo modules: reads MODULE_PREFIX, AUTHOR, ODOO_VERSION
  from .agents/.env.local; enforces one-model-per-file (py + xml), manifest
  defaults (license LGPL-3, no website, free module by default), complete
  English summary/description, and correct asset metadata. Required during
  planning for any task that creates or modifies a dn_* module.
globs: "addons/dn_*/**/*.{py,xml,csv,js,ts}"
risk: safe
---

# Module Standards Skill

## Configuration Source

All project-level defaults (module prefix, author, Odoo version) are defined in:

```
/opt/odoo16/.agents/.env.local
```

**Before starting any task on a `dn_*` module, read that file and use its values.**
If the file is missing or a key is absent, fall back to the defaults shown below.

| Key            | Default value | Purpose                              |
|----------------|---------------|--------------------------------------|
| `MODULE_PREFIX` | `dn_`        | Required prefix for module directory and technical name |
| `AUTHOR`        | `Dyan`       | Value of `author` in every manifest  |
| `ODOO_VERSION`  | `19.0`       | Target Odoo series for this workspace |

---

**Apply these rules to every Odoo module whose technical name starts with the value of `MODULE_PREFIX`.**

## Module Naming

- New modules must use a technical name beginning with `MODULE_PREFIX` (read from `.env.local`).
- Keep the module name consistent across the directory name, manifest, XML IDs, assets, and JavaScript or Python asset paths.

## Manifest Defaults

Every module whose name begins with `MODULE_PREFIX` must follow these defaults unless the user explicitly requests otherwise:

```python
{
    'author': '<AUTHOR from .env.local>',   # e.g. 'Dyan'
    'version': '<ODOO_VERSION from .env.local>.1.0',  # e.g. '19.0.1.0'
    'license': 'LGPL-3',
    # Do not add a website key by default.
    # Free modules do not define price or currency.
}
```

- Set `author` to the value of `AUTHOR` in `.env.local`.
- Set `version` to `<ODOO_VERSION>.1.0` (e.g. `19.0.1.0`) using `ODOO_VERSION` from `.env.local`.
- Do not add a `website` key by default.
- Treat the module as free by default: use a free-compatible license such as `LGPL-3` and omit `price` and `currency`.
- Only add paid-app metadata or a commercial license when the user explicitly asks for a paid module.
- Keep the manifest valid Python and preserve existing dependencies, data files, assets, and installation flags unless the task requires changing them.

## Summary and Description

- Write the manifest `summary` in English and make it describe the module's primary purpose and user value clearly.
- Write the manifest `description` in English and describe the complete feature set, not just the implementation name.
- A complete description should cover, where applicable:
  - The problem solved and the intended Odoo users.
  - The main workflows and user-visible capabilities.
  - Configuration steps and important options.
  - Supported Odoo version and required dependencies.
  - Security, access-control, automation, or integration behavior.
  - Important limitations, file formats, or operational requirements.
- Keep descriptions accurate to the code. Do not claim features that are not implemented.
- If the module has an App Store page at `static/description/index.html`, keep all visible copy in English and keep it consistent with the manifest summary and description.

## Documentation and Assets

- Use English for user-facing labels, help text, manifest metadata, README content, and App Store descriptions.
- Keep screenshots and banners in `static/description/` and reference only files that exist in the module.
- Do not introduce customer-specific names, private data, or production identifiers into demo files, screenshots, tests, or documentation.

## File Structure: One Model per File

**Every model (Python class) must live in its own dedicated file. The same applies to its XML counterpart.**

### Python (`models/`)

- One `models.Model` (or `models.TransientModel`, `models.AbstractModel`) per `.py` file.
- File name must match the model's technical name, using underscores (e.g., `stock_move.py` for `stock.move`).
- `models/__init__.py` must import every model file explicitly.

```
models/
    __init__.py          ← imports all model files
    stock_move.py        ← only StockMove class
    stock_valuation_layer.py  ← only StockValuationLayer class
    product_template.py  ← only ProductTemplate class
```

### XML (`views/`)

- One XML file per model, named `<model_name>_views.xml` (e.g., `stock_move_views.xml`).
- Each XML file contains only the views, actions, and menus that belong to that model.
- Do **not** mix views from different models into a single XML file.
- Register every view file in the manifest `data` list.

```
views/
    stock_move_views.xml
    stock_valuation_layer_views.xml
    product_template_views.xml
```

### Enforcement

- When adding a new model: create `models/<model_name>.py` **and** `views/<model_name>_views.xml` as separate files.
- When inheriting an existing Odoo model in a `dn_*` module: still create a dedicated pair of files for that model.
- Never append a new model class to an existing model file.
- Never append views for model A into the XML file of model B.

---

## Review Checklist (must pass before finishing)

Before finishing work on a `dn_*` module, verify all of the following. **None may be skipped.**

- [ ] The module directory starts with the `MODULE_PREFIX` value from `.env.local` (default: `dn_`).
- [ ] The manifest `author` matches the `AUTHOR` value from `.env.local` (default: `Dyan`).
- [ ] The manifest `version` starts with the `ODOO_VERSION` value from `.env.local` (default: `19.0`).
- [ ] No `website` key was added without an explicit request.
- [ ] The module is free and does not define paid-app metadata (unless explicitly requested).
- [ ] `summary` and `description` are complete, accurate, and written in English.
- [ ] Referenced assets exist and the manifest compiles as valid Python.
- [ ] Each model class lives in its own `.py` file under `models/`.
- [ ] Each model has a matching `views/<model_name>_views.xml` file.
- [ ] No `.py` file contains more than one model class.
- [ ] No XML file mixes views from more than one model.
- [ ] All new model files are imported in `models/__init__.py` and listed in the manifest `data`.
