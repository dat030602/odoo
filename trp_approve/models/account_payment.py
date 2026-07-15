from odoo import fields, models, api, exceptions 

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    expense_sheet_origin = fields.Integer('Nguồn bảng chi phí')