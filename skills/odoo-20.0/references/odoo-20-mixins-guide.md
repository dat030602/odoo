# Odoo 20 Mixins Guide

## Coding Conventions

- Add `'mail'` to `depends` in `__manifest__.py` when inheriting `mail.thread` or `mail.activity.mixin`.
- Always put `<chatter/>` inside `<form>` after `</sheet>` for models inheriting mail mixins.
- Set `tracking=True` on critical business fields.

---

## Table of Contents

- [Mixins Overview](#mixins-overview)
- [Chatter & Tracking (`mail.thread`)](#chatter--tracking-mailthread)
- [Scheduled Activities (`mail.activity.mixin`)](#scheduled-activities-mailactivitymixin)
- [Inbound Email Gateway (`mail.alias.mixin`)](#inbound-email-gateway-mailaliasmixin)
- [UTM Campaign Tracking (`utm.mixin`)](#utm-campaign-tracking-utmmixin)

---

## Mixins Overview

Mixins are abstract models inherited via `_inherit` that provide pre-built business workflows:

```python
class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Task'
```

---

## Chatter & Tracking (`mail.thread`)

### Python Definition
```python
class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')],
        default='draft',
        tracking=True,
    )
    user_id = fields.Many2one('res.users', tracking=True)
```

### Form View XML
In Odoo 20, the chatter is included simply using `<chatter/>`:

```xml
<form string="Task">
    <sheet>
        <!-- Form contents -->
    </sheet>
    <chatter/>
</form>
```

### Posting Messages in Python
```python
def action_notify_followers(self):
    self.message_post(
        body="Task has been started.",
        message_type='comment',
        subtype_xmlid='mail.mt_comment',
    )
```

---

## Scheduled Activities (`mail.activity.mixin`)

Inheriting `mail.activity.mixin` automatically adds activity scheduling to the chatter and activity views:

```python
def action_request_review(self):
    self.activity_schedule(
        activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
        summary="Please review task deliverables",
        user_id=self.user_id.id,
        date_deadline=fields.Date.today() + datetime.timedelta(days=2),
    )
```

---

## Inbound Email Gateway (`mail.alias.mixin`)

Allows incoming emails to automatically create or update records:

```python
class Project(models.Model):
    _name = 'project.project'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    alias_id = fields.Many2one(
        'mail.alias',
        string="Alias",
        ondelete="restrict",
        required=True,
        help="Email alias to create tasks by email",
    )

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get_id('project.task')
        values['alias_defaults'] = defaults = {'project_id': self.id}
        return values
```

---

## UTM Campaign Tracking (`utm.mixin`)

Inheriting `utm.mixin` tracks marketing attribution:

```python
class Lead(models.Model):
    _name = 'crm.lead'
    _inherit = ['mail.thread', 'utm.mixin']

    # Automatically includes campaign_id, source_id, medium_id
```

