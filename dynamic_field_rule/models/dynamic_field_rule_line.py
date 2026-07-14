from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DynamicFieldRuleLine(models.Model):
    _name = "dynamic.field.rule.line"
    _description = "Dynamic Field Rule Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    rule_id = fields.Many2one("dynamic.field.rule", required=True, ondelete="cascade")
    model_id = fields.Many2one(related="rule_id.model_id", store=True, readonly=True)
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field",
        required=True,
        domain="[('model_id', '=', model_id)]",
        ondelete="cascade",
    )
    field_name = fields.Char(related="field_id.name", store=True, readonly=True)
    field_description = fields.Char(related="field_id.field_description", store=True, readonly=True)
    field_required = fields.Boolean(related="field_id.required", store=True, readonly=True)
    required = fields.Boolean(string="Required")
    readonly = fields.Boolean(string="Readonly")
    invisible = fields.Boolean(string="Invisible")
    force = fields.Boolean(
        string="Force",
        help="Force required even when the base field is not required by the model.",
    )
    summary = fields.Char(
        string="Summary",
        compute="_compute_summary",
        readonly=True,
    )

    @api.depends("field_id", "required", "readonly", "invisible", "force")
    def _compute_summary(self):
        for line in self:
            flags = []
            base_required = bool(line.field_id.required)
            if base_required or line.required or (line.force and not base_required):
                flags.append(_("required"))
            if line.readonly:
                flags.append(_("readonly"))
            if line.invisible:
                flags.append(_("invisible"))
            if line.force and not base_required:
                flags.append(_("force"))
            elif line.force and base_required:
                flags.append(_("force ignored"))
            line.summary = ", ".join(flags) if flags else _("no override")

    @api.constrains("rule_id", "field_id")
    def _check_field_model(self):
        for line in self:
            if line.rule_id and line.field_id and line.rule_id.model_id != line.field_id.model_id:
                raise ValidationError(_("The selected field must belong to the same model as the rule."))
