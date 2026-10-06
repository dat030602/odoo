# Part of Odoo. See LICENSE file for full copyright and licensing details.

import difflib
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class DnAiImportMapping(models.Model):
    _name = "dn.ai.import.mapping"
    _description = "AI Document Import Field Mapping"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "dn.ai.import.template",
        string="Template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    scope = fields.Selection(
        [
            ("header", "Header"),
            ("line", "Line"),
        ],
        string="Scope",
        required=True,
        default="header",
    )
    target_model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        compute="_compute_target_model_id",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Target Field",
        required=True,
        ondelete="cascade",
        domain="[('model_id', '=', target_model_id)]",
    )
    field_name = fields.Char(related="field_id.name", string="Field Technical Name", readonly=True)
    field_type = fields.Selection(related="field_id.ttype", string="Field Type", readonly=True)
    relation = fields.Char(related="field_id.relation", string="Related Model", readonly=True)

    key = fields.Char(
        string="JSON Key",
        required=True,
        help="JSON property name expected from LLM output. Defaults to field technical name.",
    )
    description = fields.Char(
        string="Description / Extraction Hint",
        help="Instructions for LLM on how to find and interpret this field from the document.",
    )
    is_required = fields.Boolean(
        string="Required in Document",
        default=False,
        help="If true, schema specifies this field cannot be null.",
    )

    # Relational Matching Options
    match_field_ids = fields.Many2many(
        "ir.model.fields",
        "dn_ai_import_mapping_match_fields_rel",
        "mapping_id",
        "field_id",
        string="Match By Fields",
        domain="[('model', '=', relation)]",
        help="Fields on related model checked in order (e.g., VAT, email, name, default_code).",
    )
    match_mode = fields.Selection(
        [
            ("exact", "Exact"),
            ("ilike", "Contains (ilike)"),
            ("fuzzy", "Fuzzy Matching"),
        ],
        string="Match Mode",
        default="ilike",
        help="Method used to find existing record in database.",
    )
    fuzzy_threshold = fields.Integer(
        string="Fuzzy Threshold (%)",
        default=85,
        help="Similarity score percentage (0-100) required to consider a match.",
    )
    create_if_missing = fields.Boolean(
        string="Create if Missing",
        default=False,
        help="If no existing record matches, create a new record in related model.",
    )
    extra_domain = fields.Char(
        string="Extra Filter Domain",
        default="[]",
        help="Domain filter string applied when searching related records (e.g., [('sale_ok', '=', True)]).",
    )

    _check_fuzzy_threshold = models.Constraint(
        "CHECK (fuzzy_threshold >= 0 AND fuzzy_threshold <= 100)",
        "Fuzzy threshold must be between 0 and 100.",
    )

    @api.depends("scope", "template_id.model_id", "template_id.line_model_id")
    def _compute_target_model_id(self):
        for rec in self:
            if rec.scope == "header":
                rec.target_model_id = rec.template_id.model_id
            elif rec.scope == "line":
                rec.target_model_id = rec.template_id.line_model_id
            else:
                rec.target_model_id = False

    @api.onchange("field_id")
    def _onchange_field_id(self):
        if self.field_id and not self.key:
            self.key = self.field_id.name

    @api.constrains("template_id", "scope", "key")
    def _check_unique_key_per_scope(self):
        for rec in self:
            domain = [
                ("template_id", "=", rec.template_id.id),
                ("scope", "=", rec.scope),
                ("key", "=", rec.key),
                ("id", "!=", rec.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    _("The key '%(key)s' is already defined for %(scope)s in this template.", key=rec.key, scope=rec.scope)
                )

    def match_record(self, value):
        """Match relational records using configured match fields, modes, and thresholds."""
        self.ensure_one()
        if not value or not self.relation:
            return self.env[self.relation]

        comodel = self.env[self.relation].sudo()
        domain_base = []
        if self.extra_domain and self.extra_domain.strip():
            try:
                evaluated_domain = eval(self.extra_domain, {"datetime": fields.Datetime, "date": fields.Date})
                if isinstance(evaluated_domain, list):
                    domain_base = evaluated_domain
            except Exception:
                domain_base = []

        if self.match_field_ids:
            field_names = self.match_field_ids.mapped("name")
        else:
            rec_name = comodel._rec_name or "name"
            field_names = [rec_name] if rec_name in comodel._fields else []
            if not field_names:
                field_names = ["name"] if "name" in comodel._fields else []

        # 1. Exact match pass
        for fname in field_names:
            record = comodel.search(domain_base + [(fname, "=", value)], limit=1)
            if record:
                return record

        if self.match_mode == "exact":
            return self._handle_missing_record(value, comodel)

        # 2. ilike pass
        for fname in field_names:
            record = comodel.search(domain_base + [(fname, "ilike", value)], limit=1)
            if record:
                return record

        if self.match_mode == "ilike":
            return self._handle_missing_record(value, comodel)

        # 3. Fuzzy matching pass using difflib
        threshold_ratio = (self.fuzzy_threshold or 85) / 100.0
        best_record = None
        best_ratio = 0.0

        # Candidate selection (limit search to 500 records)
        candidates = comodel.search(domain_base, limit=500)
        str_val = str(value).lower().strip()

        for cand in candidates:
            for fname in field_names:
                cand_val = getattr(cand, fname, False)
                if not cand_val:
                    continue
                cand_str = str(cand_val).lower().strip()
                ratio = difflib.SequenceMatcher(None, str_val, cand_str).ratio()
                if ratio > best_ratio and ratio >= threshold_ratio:
                    best_ratio = ratio
                    best_record = cand

        if best_record:
            return best_record

        return self._handle_missing_record(value, comodel)

    def _handle_missing_record(self, value, comodel):
        """Create new record if create_if_missing is enabled, otherwise return empty recordset."""
        if self.create_if_missing and value:
            rec_name = comodel._rec_name or "name"
            try:
                return comodel.create({rec_name: str(value)})
            except Exception:
                return self.env[self.relation]
        return self.env[self.relation]
