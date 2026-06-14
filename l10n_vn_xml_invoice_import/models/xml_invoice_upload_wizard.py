# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class XmlInvoiceUploadWizard(models.TransientModel):
    """Wizard for uploading XML invoice files."""

    _name = "xml.invoice.upload.wizard"
    _description = "XML Invoice Upload Wizard"

    xml_file_ids = fields.Many2many("ir.attachment", string="XML Files", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    def action_upload(self):
        """Process uploaded XML files and create invoice import records."""
        self.ensure_one()

        if not self.xml_file_ids:
            raise UserError(_("Please select at least one XML file to upload."))

        import base64

        created_records = self.env["xml.invoice.import"]

        for attachment in self.xml_file_ids:

            # Skip non-xml files
            if not attachment.name.lower().endswith(".xml"):
                continue

            try:

                if not attachment.datas:
                    raise UserError(_("Empty file."))

                xml_content = base64.b64decode(attachment.datas)

                if not xml_content.strip():
                    raise UserError(_("File is empty after decoding."))

                first_part = xml_content[:50].decode("utf-8", errors="ignore").strip()

                if not (first_part.startswith("<") or first_part.startswith("<?xml")):
                    raise UserError(
                        _("Invalid XML file. Content does not start with XML tag.\nFound: %s")
                        % first_part
                    )

                # ---------------------------------------------------
                # Create invoice record
                # ---------------------------------------------------
                record = self.env["xml.invoice.import"].create_from_xml(
                    xml_content=xml_content,
                    filename=attachment.name,
                    company_id=self.company_id.id,
                )

                created_records |= record

            except Exception as e:
                raise UserError(
                    _("Failed to import file %s:\n%s")
                    % (attachment.name, str(e))
                )

        if not created_records:
            raise UserError(_("No XML files were successfully imported."))

        if len(created_records) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("XML Invoice Import"),
                "res_model": "xml.invoice.import",
                "res_id": created_records.id,
                "view_mode": "form",
                "target": "current",
            }

        return {
            "type": "ir.actions.act_window",
            "name": _("XML Invoice Imports"),
            "res_model": "xml.invoice.import",
            "view_mode": "list,form",
            "domain": [("id", "in", created_records.ids)],
            "target": "current",
        }