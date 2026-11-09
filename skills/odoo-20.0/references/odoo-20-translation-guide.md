# Odoo 20 Translation & Localization Guide

## Coding Conventions

- Always import `_` from `odoo`: `from odoo import _`.
- Always format translated strings using keyword arguments: `_("Record %(name)s not found", name=name)`. Never use `%` or f-strings with `_()`.
- Use lazy translation `_lt` for class-level dictionaries or constants: `from odoo.tools.translate import _lt`.
- Enable `translate=True` on user-facing text fields (labels, descriptions, emails).

---

## Table of Contents

- [Translating Python Code](#translating-python-code)
- [Translating Fields](#translating-fields)
- [Translating QWeb Templates](#translating-qweb-templates)
- [Translating JavaScript (OWL 3)](#translating-javascript-owl-3)
- [Exporting & Updating Translations (`i18n`)](#exporting--updating-translations-i18n)

---

## Translating Python Code

### Standard Translation Function `_()`

```python
from odoo import _, exceptions

if not task.user_id:
    raise exceptions.UserError(_("Please assign an owner to task '%(task_name)s' before starting.", task_name=task.name))
```

### Lazy Translation `_lt()`

For definitions evaluated at class import time:

```python
from odoo import fields, models
from odoo.tools.translate import _lt

STATUS_DESCRIPTIONS = {
    'draft': _lt("New / Draft"),
    'in_progress': _lt("Work In Progress"),
    'done': _lt("Completed"),
}
```

---

## Translating Fields

```python
name = fields.Char(string="Task Name", translate=True)
description = fields.Html(string="Public Details", translate=True)
```

In Odoo, translatable fields store translations as JSON dictionaries internally in PostgreSQL, allowing fast querying without join tables.

---

## Translating QWeb Templates

All static text in QWeb templates is automatically extracted for translation:

```xml
<t t-name="my_module.custom_banner">
    <div class="alert alert-info">
        <span>Welcome to your customer portal.</span>
    </div>
</t>
```

To prevent a string from being translated, use `t-translation="off"`:
```xml
<span t-translation="off">Acme ERP System v20.0</span>
```

---

## Translating JavaScript (OWL 3)

In JavaScript files, import `_t` from `@web/core/l10n/translation`:

```javascript
import { _t } from "@web/core/l10n/translation";

export class TaskNotice extends Component {
    get notificationText() {
        return _t("Task has been marked as completed!");
    }
}
```

---

## Exporting & Updating Translations (`i18n`)

### Generate or Update Module POT Template
```bash
python3 odoo-bin i18n-export --modules=my_module --output=my_module/i18n/my_module.pot -c odoo.conf -d test_db
```

### Generate PO File for Specific Language
```bash
python3 odoo-bin i18n-export --modules=my_module --lang=vi_VN --output=my_module/i18n/vi_VN.po -c odoo.conf -d test_db
```

