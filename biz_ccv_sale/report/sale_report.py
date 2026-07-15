# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

INVOICE_STATUS = [
    ('upselling', 'Upselling Opportunity'),
    ('invoiced', 'Fully Invoiced'),
    ('to invoice', 'To Invoice'),
    ('no', 'Nothing to Invoice')
]


class SaleReport(models.Model):
    _inherit = "sale.report"

    is_promotional_product = fields.Boolean(string="Is Promotional Product", readonly=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string='Province/City', readonly=True)
    district_id = fields.Many2one('res.country.district', 'District', readonly=True)
    wards_id = fields.Many2one('res.country.wards', 'Wards', readonly=True)


    picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready')],
        string='Shipping Policy')
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
    )
    has_pickable_lines = fields.Boolean('Has Pickable Lines')
    has_returnable_lines = fields.Boolean('Has Returnable Lines')
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity')
    write_date = fields.Datetime('Last Updated on')
    write_uid = fields.Many2one(
        'res.users', string='Last Updated by')

    project_id = fields.Many2one(
        'project.project', string='Project')
    
   
    
    # transaction_ids = fields.Many2many(
    #     comodel_name='payment.transaction',
    #     relation='payment_transaction_sale_report_rel', column1='sale_report_id', column2='transaction_id',
    #     string="Transactions")
    
    next_action_date = fields.Datetime(
        string="Next Action")
    
    validity_date = fields.Date(
        string="Expiration"
        )

    signed_by = fields.Char(
        string="Signed By")

    require_signature = fields.Boolean(
        string="Online Signature")

    access_token = fields.Char('Security Token')

    commitment_date = fields.Datetime(
        string="Delivery Date")
    
    effective_date = fields.Datetime("Effective Date")

    create_date = fields.Datetime("Creation Date")
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group')

    transportation = fields.Char(string="Transportation")
    sales_team_captain_id = fields.Many2one('res.users', 'Sales Team Captain')
    # tag_ids = fields.Many2many(
    #     comodel_name='crm.tag', string="Tags")

    client_order_ref = fields.Char(string="Customer Reference")

    require_payment = fields.Boolean(
        string="Online Payment")
    
    reference = fields.Char(
        string="Payment Ref.")
    
    payment_time = fields.Char(string="Payment Time")

    currency_id = fields.Many2one('res.currency', 'Currency')

    origin = fields.Char(string="Source Document")

    delivery_status = fields.Selection([
        ('pending', 'Not Delivered'),
        ('partial', 'Partially Delivered'),
        ('full', 'Fully Delivered'),
    ], string='Delivery Status')

    invoice_status = fields.Selection(
        selection=INVOICE_STATUS,
        string="Invoice Status")
    
    message_main_attachment_id = fields.Many2one(string="Main Attachment", comodel_name='ir.attachment')


    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position")
    
    incoterm_location = fields.Char(string='Incoterm Location')

    incoterm = fields.Many2one(
        'account.incoterms', 'Incoterm')
    
    signed_on = fields.Datetime(
        string="Signed On")
    
    create_uid = fields.Many2one('res.users', 'Created by')
    is_rental_order = fields.Boolean("Created In App Rental")

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string="Delivery Address",
    )

    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string="Invoice Address")
    
    sign_request_id = fields.Many2one(comodel_name="sign.request", string="Sign Request ID")
    sale_order_type_id = fields.Many2one(comodel_name="sale.order.type", string="Sale Order Type ID")

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['picking_policy'] = "s.picking_policy"
        res['payment_term_id'] = "s.payment_term_id"
        res['has_pickable_lines'] = "s.has_pickable_lines"
        res['has_returnable_lines'] = "s.has_returnable_lines"
        res['opportunity_id'] = "s.opportunity_id"
        res['write_date'] = "s.write_date"
        res['write_uid'] = "s.write_uid"
        res['project_id'] = "s.project_id"
        res['next_action_date'] = "s.next_action_date"
        res['validity_date'] = "s.validity_date"
        res['signed_by'] = "s.signed_by"
        res['require_signature'] = "s.require_signature"
        res['access_token'] = "s.access_token"
        res['commitment_date'] = "s.commitment_date"
        res['effective_date'] = "s.effective_date"
        res['create_date'] = "s.create_date"
        res['procurement_group_id'] = "s.procurement_group_id"
        res['transportation'] = "s.transportation"
        res['sales_team_captain_id'] = "s.sales_team_captain_id"
        res['client_order_ref'] = "s.client_order_ref"
        res['require_payment'] = "s.require_payment"
        res['reference'] = "s.reference"
        res['payment_time'] = "s.payment_time"
        res['currency_id'] = "s.currency_id"
        res['origin'] = "s.origin"
        res['delivery_status'] = "s.delivery_status"
        res['invoice_status'] = "s.invoice_status"
        res['message_main_attachment_id'] = "s.message_main_attachment_id"
        res['fiscal_position_id'] = "s.fiscal_position_id"
        res['incoterm_location'] = "s.incoterm_location"
        res['incoterm'] = "s.incoterm"
        res['signed_on'] = "s.signed_on"
        res['create_uid'] = "s.create_uid"
        res['is_rental_order'] = "s.is_rental_order"
        res['partner_shipping_id'] = "s.partner_shipping_id"
        res['partner_invoice_id'] = "s.partner_invoice_id"
        res['sign_request_id'] = "s.sign_request_id"
        res['sale_order_type_id'] = "s.sale_order_type_id"
        
        
        # res['transaction_ids'] = "s.transaction_ids"

        res['is_promotional_product'] = "l.is_promotional_product"
        res['state_id'] = "partner.state_id"
        res['district_id'] = "partner.district_id"
        res['wards_id'] = "partner.wards_id"
        
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.picking_policy,
            s.payment_term_id,
            s.has_pickable_lines,
            s.has_returnable_lines,
            s.opportunity_id,
            s.write_date,
            s.write_uid,
            s.project_id,
            s.next_action_date,
            s.validity_date,
            s.signed_by,
            s.require_signature,
            s.access_token,
            s.commitment_date,
            s.effective_date,
            s.create_date,
            s.procurement_group_id,
            s.transportation,
            s.sales_team_captain_id,
            s.client_order_ref,
            s.require_payment,
            s.reference,
            s.payment_time,
            s.currency_id,
            s.origin,
            s.delivery_status,
            s.invoice_status,
            s.message_main_attachment_id,
            s.fiscal_position_id,
            s.incoterm_location,
            s.incoterm,
            s.signed_on,
            s.create_uid,
            s.is_rental_order,
            s.partner_shipping_id,
            s.partner_invoice_id,
            s.sign_request_id,
            s.sale_order_type_id,

            l.is_promotional_product,
            partner.state_id,
            partner.district_id,
            partner.wards_id

            """
        return res