# Copyright (C) 2025 - Today
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class BiSQLView(models.Model):
    _inherit = "bi.sql.view"

    report_action_id = fields.Many2one(
        string="Report Action",
        comodel_name="ir.actions.report",
    )

    report_view_id = fields.Many2one(
        string="Report View",
        comodel_name="ir.ui.view",
    )

    report_page_format_id = fields.Many2one(
        string="Report Page Format",
        comodel_name="report.paperformat",
    )

    def button_create_ui(self):
        for sql_view in self:
            super().button_create_ui()
            sql_view._create_report_action()
        return True

    def button_reset_to_model_valid(self):
        for sql_view in self:
            if sql_view.report_action_id:
                sql_view.report_action_id.unlink()
            if sql_view.report_view_id:
                sql_view.report_view_id.unlink()
        return super().button_reset_to_model_valid()

    def _create_report_action(self):
        self.ensure_one()
        self.report_view_id = self.env["ir.ui.view"].create(
            self._prepare_report_view()
        ).id
        report_vals = self._prepare_report_action()
        self.report_action_id = self.env["ir.actions.report"].create(report_vals)

    def _prepare_report_action(self):
        self.ensure_one()
        return {
            "name": self.name,
            "model": self.model_id.model,
            "report_type": "qweb-pdf",
            "report_name": f"bi_sql_editor_report.bi_sql_view_report_{self.id}",
            "report_file": f"bi_sql_view_report_{self.technical_name}",
            "binding_model_id": self.model_id.id,
            "binding_type": "report",
            "print_report_name": f"{self.name}",
            "paperformat_id": self.report_page_format_id.id,
        }

    def _prepare_report_view(self):
        self.ensure_one()
        header_cells = ""
        for field in self.bi_sql_view_field_ids:
            field_name = field.field_description or field.name
            header_cells += f'<th><span>{field_name}</span></th>\n'

        data_cells = ""
        for field in self.bi_sql_view_field_ids:
            ttype = getattr(field, 'ttype', '')
            if ttype == 'datetime':
                data_cells += f'<td><span t-esc="record.{field.name} and str(record.{field.name}).split(\'.\')[0] or \'\'"/></td>\n'
            else:
                data_cells += f'<td><span t-field="record.{field.name}"/></td>\n'

        arch = f"""<odoo>
    <template id="bi_sql_view_report_{self.id}">
        <t t-call="web.html_container">
            <t t-call="web.external_layout">
                <div class="page">
                    <h2>{self.name}</h2>
                    <table class="table table-condensed">
                        <thead>
                            <tr>
                                {header_cells}
                            </tr>
                        </thead>
                        <tbody>
                            <tr t-foreach="docs" t-as="record">
                                {data_cells}
                            </tr>
                        </tbody>
                    </table>
                </div>
            </t>
        </t>
    </template>
</odoo>"""

        return {
            "name": f"{self.name} Report",
            "type": "qweb",
            "mode": "primary",
            "arch": arch,
            "key": f"bi_sql_editor_report.bi_sql_view_report_{self.id}",
        }