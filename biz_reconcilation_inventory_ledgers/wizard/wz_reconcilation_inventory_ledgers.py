from odoo import fields, models, api


class ReconcilationInventoryLedgersWizard(models.TransientModel):
    _name = 'reconcilation.inventory.legers.wizard' 
    _description = 'Reconcilation Inventory and Ledgers Wizard'
    
    from_date = fields.Date('Date From', default=fields.Date.today)
    to_date = fields.Date('Date To', default=fields.Date.today)
    
    def action_print(self):
        return self.env.ref('biz_reconcilation_inventory_ledgers.action_report_reconcilation_xlsx').report_action(self)