# Odoo 20 Manifest Guide

## Coding Conventions

- Load security before views, and actions before menus.
- In `data:`, declare `security/<module>_groups.xml` followed by `security/ir.access.csv`.
- Never include `ir.model.access.csv` (use `ir.access.csv`).
- Target Python 3.12+ and PostgreSQL 16+.

---

## Table of Contents

- [Manifest Overview](#manifest-overview)
- [Manifest Keys Reference](#manifest-keys-reference)
- [Data File Loading Order](#data-file-loading-order)
- [Assets Bundles](#assets-bundles)
- [Module Lifecycle Hooks](#module-lifecycle-hooks)

---

## Manifest Overview

Every Odoo module must include a `__manifest__.py` file in its root directory.

### Example Manifest

```python
{
    'name': "Sales Customization",
    'version': '20.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Extends sales workflow with custom approvals and pricing",
    'author': "My Company",
    'website': "https://www.example.com",
    'license': 'LGPL-3',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/sales_custom_groups.xml',
        'security/ir.access.csv',
        'data/sequence_data.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
        'report/sale_order_reports.xml',
    ],
    'demo': [
        'demo/sale_order_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'my_module/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'my_module/static/tests/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
}
```

---

## Manifest Keys Reference

| Key | Type | Description |
|-----|------|-------------|
| `name` | str (required) | Module title displayed in Apps |
| `version` | str (required) | Module version (convention: `20.0.x.y.z`) |
| `depends` | list[str] | Module dependencies that must be installed first |
| `data` | list[str] | XML/CSV data files to load at install/upgrade |
| `demo` | list[str] | Demonstration data loaded only if demo data is enabled |
| `assets` | dict[str, list] | Asset bundles for OWL components, CSS, SCSS, JS |
| `license` | str | Software license (`'LGPL-3'`, `'OEEL-1'`, `'OPL-1'`, etc.) |
| `installable` | bool | Whether the module can be installed (default: `True`) |
| `application` | bool | Whether module is featured as a standalone app in App list |
| `auto_install` | bool/list | Auto-installs if all specified modules are installed |

---

## Data File Loading Order

Files in `data:` are loaded strictly sequentially. A dependable ordering is:

1. **Security Groups & Privileges**: `security/<module>_groups.xml`
2. **Access Rights & Restrictions**: `security/ir.access.csv`
3. **Sequences & Base Records**: `data/<module>_data.xml`
4. **Action Windows & Server Actions**: `views/<model>_actions.xml`
5. **Views (form, list, search, kanban)**: `views/<model>_views.xml`
6. **Menu Items**: `views/<module>_menus.xml`
7. **Reports & Paper Formats**: `report/<model>_reports.xml`
8. **Mail & Activity Templates**: `data/mail_template_data.xml`

---

## Assets Bundles

Odoo 20 uses standard asset bundles:

```python
'assets': {
    'web.assets_backend': [
        'my_module/static/src/components/**/*.js',
        'my_module/static/src/components/**/*.xml',
        'my_module/static/src/scss/**/*.scss',
    ],
    'web.assets_frontend': [
        'my_module/static/src/portal/**/*',
    ],
    # Hoot test suite in Odoo 20
    'web.assets_unit_tests': [
        'my_module/static/tests/**/*.test.js',
    ],
}
```

---

## Module Lifecycle Hooks

```python
# In __init__.py of module:
from . import controllers
from . import models

def _post_init_hook(env):
    """Executes after module data has been loaded."""
    env['my.model']._initialize_default_settings()

def _uninstall_hook(env):
    """Executes when module is being uninstalled."""
    env['ir.config_parameter'].sudo().search([('key', '=like', 'my_module.%')]).unlink()
```

Referenced in `__manifest__.py`:
```python
'post_init_hook': '_post_init_hook',
'uninstall_hook': '_uninstall_hook',
```

