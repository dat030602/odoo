from odoo import fields, models, api


class rp_ccv_inventory_export(models.AbstractModel):
    _name = 'report.biz_ccv_sale.rp_ccv_inventory_export'
    _description = 'rp_ccv_inventory_export'

    def get_account(self, o):
        debit = []
        credit = []
        for line in o.move_ids_without_package:
            categ = line.product_id.categ_id
            if categ.property_stock_valuation_account_id:
                if categ.property_stock_valuation_account_id.code not in debit:
                    debit.append(categ.property_stock_valuation_account_id.code)
            if categ.property_stock_account_input_categ_id:
                if categ.property_stock_account_input_categ_id.code not in credit:
                    credit.append(categ.property_stock_account_input_categ_id.code)

        debit_account = debit and ', '.join(debit) or ''
        credit_account = credit and ', '.join(credit) or ''
        return [debit_account, credit_account]

    def format_decimal(self, number):
        if not number:
            return 0
        string = '{:,.3f}'.format(number).split('.')
        return '%s,%s' % (string[0].replace(',', '.'), string[1])

    def get_delivery_user_name(self, picking_id):
        delivery_user_name = ''
        if picking_id.mrp_production_id:
            delivery_user_name = picking_id.mrp_production_id.user_id.name_without_position
        elif picking_id.partner_id:
            delivery_user_name = picking_id.partner_id.name
        return delivery_user_name

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env['stock.picking']
        docs = model.browse(docids[0])
        return {
            'doc_model': model,
            'docs': docs,
            'data': data,
            'get_account': self.get_account,
            'format_decimal': self.format_decimal,
            'get_delivery_user_name': self.get_delivery_user_name,
        }
