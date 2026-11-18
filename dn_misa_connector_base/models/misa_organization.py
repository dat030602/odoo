import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MisaOrganization(models.Model):
    _name = 'misa.organization'
    _description = 'MISA INBOT Organization / Department'
    _order = 'org_name, id'

    name = fields.Char(string='Organization Name', compute='_compute_name', store=True)
    org_id = fields.Char(string='MISA Organization ID', required=True, index=True)
    org_code = fields.Char(string='Organization Code')
    org_name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    parent_org_id = fields.Char(string='Parent MISA Org ID')
    parent_id = fields.Many2one('misa.organization', string='Parent Organization', compute='_compute_parent_id', store=True)

    # Subscription / Pack Quotas associated with Organization
    product_pack_code = fields.Char(string='Pack Code')
    start_date = fields.Date(string='Start Date')
    expired_date = fields.Date(string='Expired Date')
    number_of_invoice = fields.Integer(string='Total Invoices')
    number_inv_used = fields.Integer(string='Invoices Used')
    number_inv_still = fields.Integer(string='Invoices Remaining')
    status = fields.Selection([
        ('0', 'Official (Standard)'),
        ('1', 'Official (Active)'),
        ('2', 'Trial'),
    ], string='Pack Status')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('org_company_uniq', 'unique(org_id, company_id)', 'Organization ID must be unique per Company!')
    ]

    @api.depends('org_name', 'org_code')
    def _compute_name(self):
        for rec in self:
            if rec.org_code:
                rec.name = f"[{rec.org_code}] {rec.org_name}"
            else:
                rec.name = rec.org_name or rec.org_id

    @api.depends('parent_org_id', 'company_id')
    def _compute_parent_id(self):
        for rec in self:
            if rec.parent_org_id:
                parent = self.search([
                    ('org_id', '=', rec.parent_org_id),
                    ('company_id', '=', rec.company_id.id)
                ], limit=1)
                rec.parent_id = parent.id
            else:
                rec.parent_id = False

    @api.model
    def sync_organizations(self, company):
        """Synchronize organizations from MISA INBOT for the specified company."""
        if not company.misa_inbot_subscribers_id:
            # Try fetching subscriber id first
            if company.misa_tax_code:
                endpoint_sub = f"meinvoicebot/v1/subscribers/code/{company.misa_tax_code}"
                res_sub = company._execute_inbot_api(endpoint_sub, method='GET')
                if res_sub['is_success'] and isinstance(res_sub['data'], dict):
                    data_obj = res_sub['data'].get('Data') or res_sub['data']
                    sub_id = data_obj.get('Id') if isinstance(data_obj, dict) else False
                    if sub_id:
                        company.misa_inbot_subscribers_id = str(sub_id)

        if not company.misa_inbot_subscribers_id:
            raise UserError(_("SubscribersId (CompanyID) could not be resolved. Please verify Tax Code and login."))

        endpoint = f"meinvoicebot/v1/{company.misa_inbot_subscribers_id}/organizations"
        res = company._execute_inbot_api(endpoint, method='GET')

        if not res['is_success']:
            raise UserError(_("Failed to fetch organizations: %s (%s)") % (res['error_message'], res['error_code']))

        data = res['data']
        org_list = []
        if isinstance(data, dict):
            org_list = data.get('Data') or []
            if not isinstance(org_list, list):
                org_list = [org_list]
        elif isinstance(data, list):
            org_list = data

        synced_count = 0
        for item in org_list:
            if not isinstance(item, dict):
                continue
            org_id = str(item.get('Id') or item.get('OrganizationID') or item.get('OrgId') or '')
            if not org_id:
                continue

            vals = {
                'org_id': org_id,
                'org_code': item.get('OrganizationCode') or item.get('OrgCode') or '',
                'org_name': item.get('OrganizationName') or item.get('OrgName') or item.get('Name') or org_id,
                'parent_org_id': str(item.get('ParentID') or item.get('ParentOrgId') or '') or False,
                'company_id': company.id,
            }

            # Optional quota details if provided in organization payload
            if 'ProductPackCode' in item:
                vals['product_pack_code'] = item.get('ProductPackCode')
            if 'NumberOfInvoice' in item:
                vals['number_of_invoice'] = item.get('NumberOfInvoice') or 0
            if 'NumberInvUsed' in item:
                vals['number_inv_used'] = item.get('NumberInvUsed') or 0
            if 'NumberInvStill' in item:
                vals['number_inv_still'] = item.get('NumberInvStill') or 0

            existing = self.search([
                ('org_id', '=', org_id),
                ('company_id', '=', company.id)
            ], limit=1)

            if existing:
                existing.write(vals)
            else:
                self.create(vals)
            synced_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Organizations Synchronized'),
                'message': _('Successfully synchronized %s organization(s) for company %s.') % (synced_count, company.name),
                'type': 'success',
                'sticky': False,
            }
        }
