# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class DnAiImportWizard(models.TransientModel):
    _name = "dn.ai.import.wizard"
    _description = "AI Document Import Wizard"

    template_id = fields.Many2one(
        "dn.ai.import.template",
        string="Import Template",
        required=True,
        readonly=True,
    )
    res_model = fields.Char(string="Destination Model", readonly=True)
    res_id = fields.Integer(string="Destination Record ID", readonly=True)

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "dn_ai_import_wizard_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Documents (PDF / Images)",
        help="Upload PDF documents or images (PNG, JPG, TIFF) to digitize.",
    )
    state = fields.Selection(
        [
            ("upload", "Upload Document"),
            ("preview", "Preview & Validate"),
        ],
        string="State",
        default="upload",
        required=True,
    )
    raw_json = fields.Text(
        string="Raw Extracted JSON",
        help="Editable JSON response returned from AI model.",
    )
    value_ids = fields.One2many(
        "dn.ai.import.wizard.value",
        "wizard_id",
        string="Extracted Values",
    )

    def action_extract(self):
        """Call AI model and prepare preview line items."""
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_("Please upload at least one PDF or image document."))

        data = self.template_id.extract_document(self.attachment_ids)
        self.raw_json = json.dumps(data, indent=2, ensure_ascii=False)
        self._populate_preview_values(data)
        self.state = "preview"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _populate_preview_values(self, data):
        """Transform JSON response into editable preview rows."""
        self.value_ids.unlink()
        vals_list = []

        # 1. Header values
        for mapping in self.template_id.mapping_ids:
            raw_val = data.get(mapping.key)
            status = "matched"
            matched_res_id = False

            if mapping.field_type in ("many2one", "many2many") and raw_val:
                record = mapping.match_record(raw_val)
                if record:
                    matched_res_id = record.id
                    status = "matched"
                else:
                    status = "not_found"
            elif raw_val is None or raw_val == "":
                status = "skipped"

            vals_list.append({
                "wizard_id": self.id,
                "mapping_id": mapping.id,
                "scope": "header",
                "line_index": 0,
                "key": mapping.key,
                "field_name": mapping.field_id.field_description or mapping.field_name,
                "raw_value": str(raw_val) if raw_val is not None else "",
                "matched_res_id": matched_res_id,
                "status": status,
            })

        # 2. Line items
        lines_data = data.get("lines") or []
        for idx, line_dict in enumerate(lines_data, start=1):
            for lm in self.template_id.line_mapping_ids:
                raw_val = line_dict.get(lm.key)
                status = "matched"
                matched_res_id = False

                if lm.field_type in ("many2one", "many2many") and raw_val:
                    record = lm.match_record(raw_val)
                    if record:
                        matched_res_id = record.id
                        status = "matched"
                    else:
                        status = "not_found"
                elif raw_val is None or raw_val == "":
                    status = "skipped"

                vals_list.append({
                    "wizard_id": self.id,
                    "mapping_id": lm.id,
                    "scope": "line",
                    "line_index": idx,
                    "key": lm.key,
                    "field_name": lm.field_id.field_description or lm.field_name,
                    "raw_value": str(raw_val) if raw_val is not None else "",
                    "matched_res_id": matched_res_id,
                    "status": status,
                })

        self.env["dn.ai.import.wizard.value"].create(vals_list)

    def action_back(self):
        """Return to upload step."""
        self.ensure_one()
        self.state = "upload"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_confirm(self):
        """Apply previewed / validated values to destination record."""
        self.ensure_one()
        dest_model_name = self.template_id.model_name
        dest_model = self.env[dest_model_name]

        header_vals = {}
        for val in self.value_ids.filtered(lambda v: v.scope == "header" and v.status != "skipped"):
            mapping = val.mapping_id
            fname = mapping.field_name
            if mapping.field_type == "many2one":
                header_vals[fname] = val.matched_res_id or False
            elif mapping.field_type == "many2many":
                header_vals[fname] = [Command.set([val.matched_res_id])] if val.matched_res_id else False
            elif mapping.field_type in ("float", "monetary"):
                try:
                    header_vals[fname] = float(val.raw_value.replace(",", "").strip())
                except Exception:
                    header_vals[fname] = 0.0
            elif mapping.field_type == "integer":
                try:
                    header_vals[fname] = int(val.raw_value.strip())
                except Exception:
                    header_vals[fname] = 0
            elif mapping.field_type == "boolean":
                header_vals[fname] = val.raw_value.lower() in ("true", "1", "yes")
            else:
                header_vals[fname] = val.raw_value

        # Build Line commands if configured
        if self.template_id.line_field_id:
            line_field_name = self.template_id.line_field_name
            line_cmds = []
            if self.res_id and self.template_id.replace_lines:
                line_cmds.append(Command.clear())

            # Group line values by line_index
            line_indices = sorted(list({v.line_index for v in self.value_ids if v.scope == "line"}))
            for l_idx in line_indices:
                l_vals = {}
                row_items = self.value_ids.filtered(lambda v: v.scope == "line" and v.line_index == l_idx)
                for item in row_items:
                    mapping = item.mapping_id
                    fname = mapping.field_name
                    if mapping.field_type == "many2one":
                        l_vals[fname] = item.matched_res_id or False
                    elif mapping.field_type == "many2many":
                        l_vals[fname] = [Command.set([item.matched_res_id])] if item.matched_res_id else False
                    elif mapping.field_type in ("float", "monetary"):
                        try:
                            l_vals[fname] = float(item.raw_value.replace(",", "").strip())
                        except Exception:
                            l_vals[fname] = 0.0
                    elif mapping.field_type == "integer":
                        try:
                            l_vals[fname] = int(item.raw_value.strip())
                        except Exception:
                            l_vals[fname] = 0
                    else:
                        l_vals[fname] = item.raw_value

                if any(v for v in l_vals.values() if v is not False and v != ""):
                    line_cmds.append(Command.create(l_vals))

            if line_cmds:
                header_vals[line_field_name] = line_cmds

        # Write or Create record
        if self.res_id and self.res_model == dest_model_name:
            target_record = dest_model.browse(self.res_id)
            target_record.write(header_vals)
        else:
            target_record = dest_model.create(header_vals)

        # Attach source documents & log chatter
        if self.template_id.attach_document and self.attachment_ids:
            self.attachment_ids.write({
                "res_model": dest_model_name,
                "res_id": target_record.id,
            })
            if hasattr(target_record, "message_post"):
                target_record.message_post(
                    body=_("Document digitized and imported using AI Template: <b>%s</b>", self.template_id.name),
                    attachment_ids=self.attachment_ids.ids,
                )

        return {
            "type": "ir.actions.act_window",
            "name": target_record.display_name,
            "res_model": dest_model_name,
            "res_id": target_record.id,
            "view_mode": "form",
            "target": "current",
        }


class DnAiImportWizardValue(models.TransientModel):
    _name = "dn.ai.import.wizard.value"
    _description = "AI Document Wizard Preview Value"
    _order = "scope desc, line_index, id"

    wizard_id = fields.Many2one("dn.ai.import.wizard", required=True, ondelete="cascade")
    mapping_id = fields.Many2one("dn.ai.import.mapping", required=True, ondelete="cascade")
    scope = fields.Selection([("header", "Header"), ("line", "Line")], required=True)
    line_index = fields.Integer(string="Line #", default=0)
    key = fields.Char(string="Key", required=True)
    field_name = fields.Char(string="Target Field")
    raw_value = fields.Char(string="Extracted Text / Value")
    relation = fields.Char(related="mapping_id.relation", readonly=True)

    matched_res_id = fields.Integer(string="Matched Record ID")
    matched_record_display = fields.Char(
        string="Matched Record",
        compute="_compute_matched_record_display",
    )
    status = fields.Selection(
        [
            ("matched", "Matched"),
            ("not_found", "Not Found"),
            ("skipped", "Skipped / Empty"),
        ],
        string="Status",
        default="matched",
    )

    @api.depends("matched_res_id", "relation")
    def _compute_matched_record_display(self):
        for rec in self:
            if rec.relation and rec.matched_res_id:
                try:
                    target = self.env[rec.relation].sudo().browse(rec.matched_res_id)
                    rec.matched_record_display = target.display_name or f"ID {rec.matched_res_id}"
                except Exception:
                    rec.matched_record_display = f"ID {rec.matched_res_id}"
            else:
                rec.matched_record_display = False
