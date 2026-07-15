from odoo import api, fields, models, _
from datetime import datetime, timedelta

class rp_summary_ie_inv_pdf(models.AbstractModel):
    _inherit = 'report.biz_stock_summary_report.rp_summary_ie_inv_pdf'

    def get_line(self,o):
        lines = []
        if not o.warehouse_id:
            warehouses = o.line_ids.filtered(lambda x: x.warehouse_id).mapped('warehouse_id')
            #tổng hợp theo kho
            for ware in warehouses:
                lines.append([ware,o.line_ids.filtered(lambda x: x.warehouse_id == ware)])
            #tổng hợp các sản phẩm kh có kho
            lines.append([False,o.line_ids.filtered(lambda x: not x.warehouse_id)])
        else:
            lines.append([o.warehouse_id,o.line_ids])
        return lines

    def sum_qty_warehouse(self, line_ids):
        qty_begin = tt_begin = 0
        qty_import = tt_import = 0
        qty_export = tt_export = 0
        qty_end = tt_end = 0

        for line in line_ids:
            qty_begin += line.qty_begin
            tt_begin += line.tt_begin
            qty_import += line.qty_import
            tt_import += line.tt_import
            qty_export += line.qty_export
            tt_export += line.tt_export
            qty_end += line.qty_end
            tt_end += line.tt_end

        return {
            'qty_begin': qty_begin,
            'tt_begin': tt_begin,
            'qty_import': qty_import,
            'tt_import': tt_import,
            'qty_export': qty_export,
            'tt_export': tt_export,
            'qty_end': qty_end,
            'tt_end': tt_end,
        }

    def format_float_number(self, num, qty=False):
        if not num:
            return 0

        number = float(num)
        if not qty:
            return "{:,.0f}".format(number)
        else:
            number_format = "{:,.3f}".format(number)
            return number_format

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super(rp_summary_ie_inv_pdf,self)._get_report_values(docids,data=data)
        res.update({
            'get_line': self.get_line,
            'sum_qty_warehouse': self.sum_qty_warehouse
        })
        return res