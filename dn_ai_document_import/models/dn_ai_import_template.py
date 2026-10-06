# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo import api, fields, models
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai.utils.llm_providers import PROVIDERS, get_provider
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class DnAiImportTemplate(models.Model):
    _name = "dn.ai.import.template"
    _description = "AI Document Import Template"
    _order = "name"

    @api.model
    def _get_llm_model_selection(self):
        selection = []
        for provider in PROVIDERS:
            selection.extend(provider.llms)
        return selection

    name = fields.Char(string="Template Name", required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        help="Leave blank to use across all companies.",
    )
    llm_model = fields.Selection(
        selection=_get_llm_model_selection,
        string="LLM Model",
        default="gemini-2.5-flash",
        required=True,
        help="Multimodal LLM model used for OCR and data extraction.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Destination Model",
        required=True,
        ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", string="Model Technical Name", readonly=True, store=True)
    line_field_id = fields.Many2one(
        "ir.model.fields",
        string="Lines Field (One2many)",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'one2many')]",
        help="Optional One2many field representing document lines/items.",
    )
    line_field_name = fields.Char(related="line_field_id.name", readonly=True)
    line_model_id = fields.Many2one(
        "ir.model",
        string="Line Model",
        compute="_compute_line_model_id",
        store=True,
    )

    prompt = fields.Text(
        string="Extraction Instructions (Prompt)",
        required=True,
        default="Extract all document metadata and item lines accurately from the provided document.",
    )
    mapping_ids = fields.One2many(
        "dn.ai.import.mapping",
        "template_id",
        string="Header Field Mappings",
        domain=[("scope", "=", "header")],
    )
    line_mapping_ids = fields.One2many(
        "dn.ai.import.mapping",
        "template_id",
        string="Line Item Mappings",
        domain=[("scope", "=", "line")],
    )

    replace_lines = fields.Boolean(
        string="Replace Existing Lines",
        default=False,
        help="When updating an existing record, clear old lines before importing new ones.",
    )
    attach_document = fields.Boolean(
        string="Attach Source Document",
        default=True,
        help="Attach source uploaded files to the resulting record.",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "dn_ai_import_template_groups_rel",
        "template_id",
        "group_id",
        string="Allowed User Groups",
        help="If set, only users belonging to these groups will see the Action menu button.",
    )
    action_id = fields.Many2one(
        "ir.actions.server",
        string="Linked Server Action",
        readonly=True,
        copy=False,
    )
    json_schema = fields.Text(
        string="Generated JSON Schema",
        compute="_compute_json_schema",
    )

    @api.depends("line_field_id")
    def _compute_line_model_id(self):
        for rec in self:
            if rec.line_field_id and rec.line_field_id.relation:
                rec.line_model_id = self.env["ir.model"].search(
                    [("model", "=", rec.line_field_id.relation)], limit=1
                )
            else:
                rec.line_model_id = False

    @api.depends("mapping_ids", "line_mapping_ids", "line_field_id")
    def _compute_json_schema(self):
        for rec in self:
            rec.json_schema = json.dumps(rec._build_json_schema(), indent=2)

    def _get_schema_property(self, mapping):
        """Map Odoo field type to OpenAI/Gemini strict compatible JSON schema property."""
        ttype = mapping.field_type or "char"
        is_req = mapping.is_required
        desc = mapping.description or mapping.key

        type_map = {
            "boolean": ["boolean"] if is_req else ["boolean", "null"],
            "integer": ["integer"] if is_req else ["integer", "null"],
            "float": ["number"] if is_req else ["number", "null"],
            "monetary": ["number"] if is_req else ["number", "null"],
            "date": ["string"] if is_req else ["string", "null"],
            "datetime": ["string"] if is_req else ["string", "null"],
        }
        prop_type = type_map.get(ttype, ["string"] if is_req else ["string", "null"])

        prop = {
            "type": prop_type if len(prop_type) > 1 else prop_type[0],
            "description": desc,
        }
        if ttype in ("date", "datetime"):
            prop["description"] += " (Format: YYYY-MM-DD or ISO datetime)"
        return prop

    def _build_json_schema(self):
        """Build strict-compatible JSON schema."""
        self.ensure_one()
        properties = {}
        required_keys = []

        # 1. Header mappings
        for m in self.mapping_ids:
            properties[m.key] = self._get_schema_property(m)
            required_keys.append(m.key)

        # 2. Line mappings
        if self.line_field_id and self.line_mapping_ids:
            line_properties = {}
            line_required_keys = []
            for lm in self.line_mapping_ids:
                line_properties[lm.key] = self._get_schema_property(lm)
                line_required_keys.append(lm.key)

            properties["lines"] = {
                "type": "array",
                "description": "List of line items or order rows",
                "items": {
                    "type": "object",
                    "properties": line_properties,
                    "required": line_required_keys,
                    "additionalProperties": False,
                },
            }
            required_keys.append("lines")

        return {
            "type": "object",
            "properties": properties,
            "required": required_keys,
            "additionalProperties": False,
        }

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._sync_server_action()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ("name", "model_id", "group_ids", "active")):
            self._sync_server_action()
        return res

    def unlink(self):
        actions = self.mapped("action_id")
        res = super().unlink()
        if actions:
            actions.unlink()
        return res

    def _sync_server_action(self):
        """Create or update ir.actions.server binding on target model to open import wizard."""
        for rec in self:
            if not rec.model_id:
                continue

            action_vals = {
                "name": _("Import with AI: %s", rec.name),
                "model_id": rec.model_id.id,
                "binding_model_id": rec.model_id.id if rec.active else False,
                "binding_view_types": "list,form",
                "state": "code",
                "group_ids": [(6, 0, rec.group_ids.ids)],
                "code": (
                    f"action = env['dn.ai.import.template'].browse({rec.id}).action_open_wizard()"
                ),
            }

            if rec.action_id:
                rec.action_id.write(action_vals)
            else:
                action = self.env["ir.actions.server"].sudo().create(action_vals)
                rec.action_id = action

    def action_open_wizard(self):
        """Open the import wizard with template and caller context."""
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        wizard = self.env["dn.ai.import.wizard"].create({
            "template_id": self.id,
            "res_model": active_model if active_id else False,
            "res_id": active_id or False,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Import Document: %s", self.name),
            "res_model": "dn.ai.import.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def extract_document(self, attachments):
        """Call LLMApiService with template configuration and attachments."""
        self.ensure_one()
        if not attachments:
            raise UserError(_("Please upload at least one document or image to proceed."))

        files = []
        for att in attachments:
            if not att.datas:
                continue
            mimetype = att.mimetype or "application/octet-stream"
            b64_val = att.datas.decode("utf-8") if isinstance(att.datas, bytes) else att.datas
            files.append({
                "mimetype": mimetype,
                "value": b64_val,
                "file_ref": f"<file_#{att.id}>",
            })

        if not files:
            raise UserError(_("No readable document files found in attachments."))

        llm_model = self.llm_model or "gemini-2.5-flash"
        provider = get_provider(self.env, llm_model)
        schema = self._build_json_schema()

        service = LLMApiService(env=self.env, provider=provider)
        system_prompts = [
            "You are an expert AI document extraction assistant. Output strictly valid JSON matching the schema."
        ]
        user_prompts = [self.prompt]

        try:
            responses = service.request_llm(
                llm_model=llm_model,
                system_prompts=system_prompts,
                user_prompts=user_prompts,
                files=files,
                schema=schema,
                temperature=0.0,
            )
        except Exception as e:
            _logger.exception("AI Extraction Request Failed")
            raise UserError(_("AI Extraction failed: %s", str(e)))

        if not responses or not responses[0]:
            raise UserError(_("No response received from AI model."))

        try:
            parsed_data = json.loads(responses[0])
            return parsed_data
        except Exception:
            _logger.error("Failed to parse AI JSON response: %s", responses[0])
            raise UserError(_("AI returned an invalid JSON response:\n%s", responses[0]))
