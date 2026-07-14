from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DynamicFieldRule(models.Model):
    _name = "dynamic.field.rule"
    _description = "Dynamic Field Rule"
    _order = "priority, name, id"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade", index=True)
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    priority = fields.Integer(default=100)
    user_ids = fields.Many2many("res.users", string="Users")
    group_ids = fields.Many2many("res.groups", string="Groups")
    apply_form = fields.Boolean(string="Form", default=True)
    apply_tree = fields.Boolean(string="Tree", default=True)
    apply_kanban = fields.Boolean(string="Kanban", default=False)
    condition = fields.Text(string="Condition")
    description = fields.Text(string="Description")
    rule_line_ids = fields.One2many(
        "dynamic.field.rule.line",
        "rule_id",
        string="Field Rules",
    )
    preview_text = fields.Text(
        string="Preview",
        compute="_compute_preview_text",
        readonly=True,
    )
    affected_field_summary = fields.Text(
        string="Affected Fields",
        compute="_compute_affected_field_summary",
        readonly=True,
    )

    @api.depends("user_ids", "group_ids", "apply_form", "apply_tree", "apply_kanban", "condition")
    def _compute_preview_text(self):
        for rule in self:
            applied_users = ", ".join(rule.user_ids.mapped("display_name")) or _("All users")
            applied_groups = ", ".join(rule.group_ids.mapped("display_name")) or _("All groups")
            apply_on = []
            if rule.apply_form:
                apply_on.append(_("Form"))
            if rule.apply_tree:
                apply_on.append(_("Tree"))
            if rule.apply_kanban:
                apply_on.append(_("Kanban"))

            preview_lines = [
                _("Applied Users: %s") % applied_users,
                _("Applied Groups: %s") % applied_groups,
                _("Apply On: %s") % (", ".join(apply_on) if apply_on else _("None")),
            ]
            if rule.condition:
                preview_lines.append(_("Condition: %s") % rule.condition)
            rule.preview_text = "\n".join(preview_lines)

    @api.depends(
        "rule_line_ids.field_id",
        "rule_line_ids.required",
        "rule_line_ids.readonly",
        "rule_line_ids.invisible",
        "rule_line_ids.force",
        "rule_line_ids.summary",
    )
    def _compute_affected_field_summary(self):
        for rule in self:
            lines = []
            for line in rule.rule_line_ids.sorted(lambda item: (item.sequence, item.id)):
                if not line.field_id:
                    continue
                field_label = line.field_id.field_description or line.field_id.name
                lines.append(f"{field_label}: {line.summary}")
            rule.affected_field_summary = "\n".join(lines) or _("No field rules defined yet.")
