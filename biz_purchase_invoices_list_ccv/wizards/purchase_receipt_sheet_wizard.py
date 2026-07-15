# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models, _


class PurchaseReceiptSheetWizard(models.TransientModel):
    _name = 'purchase.receipt.sheet.wizard.ccv'
    _description = 'Purchase Receipt Sheet Wizard CCV'
    
    date_from = fields.Date('Date From', required=True)
    date_to = fields.Date('Date To', required=True)
    
    def action_print(self):
        """Create record and generate data, then print report"""
        self.ensure_one()
        
        # Create sheet record
        sheet = self.env['purchase.invoices.list.ccv'].create({
            'name': 'BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ MUA VÀO',
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        
        # Generate lines
        sheet.action_generate()
        
        # Return action to print report
        return self.env.ref('biz_purchase_invoices_list_ccv.action_purchase_receipt_sheet_ccv').report_action(sheet)


