from odoo import fields, models, api

from odoo.addons.biz_accounting_voucher_ccv.config import amount_to_text,format_float_number

def get_address(partner_id):
    if not partner_id:
        return ''
    address_parts = []
    
    if partner_id.street:
        address_parts.append(partner_id.street)
    
    if partner_id.wards_id:
        address_parts.append(partner_id.wards_id.name) 
    
    if partner_id.district_id:
        address_parts.append(partner_id.district_id.name)
    
    if partner_id.state_id:
        address_parts.append(partner_id.state_id.name)
    
    if partner_id.country_id:
        address_parts.append(partner_id.country_id.name)

    full_address = ', '.join(address_parts)
    return full_address

class rp_vourcher_receipt(models.AbstractModel):
    _name = 'report.biz_accounting_voucher_receipt.i_rp_vourcher_receipt'
    _description = 'rp_vourcher_receipt'

    def get_lines(self, move):
        lines = {}
        for line in move.line_ids:
            account = line.account_id.code
            if '/' not in lines:
                lines['/'] = {
                    'name': line.name,
                    'debit': line.debit > 0 and [account] or [],
                    'credit': line.credit > 0 and [account] or [],
                    'amount': line.debit > 0 and line.debit or 0
                }
            else:
                if line.debit > 0:
                    if account not in lines['/']['debit']:
                        lines['/']['debit'].append(account)
                    
                    lines['/']['amount'] += line.debit
                
                if line.credit > 0:
                    if account not in lines['/']['credit']:
                        lines['/']['credit'].append(account)
       
        for line in lines.values():
            line['debit'] = ','.join(line['debit'])
            line['credit'] = ','.join(line['credit'])

        return lines.values()

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env['account.move']
        docs = model.browse(docids)
        return {
            'doc_model': model,
            'docs': docs,
            'amount_to_text': amount_to_text,
            'format_float_number': format_float_number,
            'get_lines': self.get_lines,
            'get_address': get_address
        }
