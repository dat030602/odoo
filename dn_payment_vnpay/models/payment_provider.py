# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('vnpay', 'VNPay')],
        ondelete={'vnpay': 'set default'}
    )
    
    vnpay_tmn_code = fields.Char(
        string="VNPay TMN Code",
        groups="base.group_system",
        help="Terminal code provided by VNPay"
    )
    vnpay_hash_secret = fields.Char(
        string="VNPay Hash Secret",
        groups="base.group_system",
        help="Secret key used to generate HMAC-SHA512 checksum"
    )
    
    connector_provider_id = fields.Many2one(
        'connector.provider',
        string='Connector Provider',
        compute='_compute_connector_provider_id',
        store=False,
    )

    def _compute_connector_provider_id(self):
        vnpay_conn = self.env['connector.provider'].sudo().search([('code', '=', 'vnpay')], limit=1)
        for rec in self:
            rec.connector_provider_id = vnpay_conn if rec.code == 'vnpay' else False

    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'vnpay':
            return default_codes
        return ['card', 'unknown']

    def write(self, vals):
        res = super().write(vals)
        if 'vnpay_tmn_code' in vals or 'vnpay_hash_secret' in vals:
            for provider in self.filtered(lambda p: p.code == 'vnpay'):
                conn = self.env['connector.provider'].sudo().search([('code', '=', 'vnpay')], limit=1)
                if conn:
                    if 'vnpay_tmn_code' in vals and vals['vnpay_tmn_code']:
                        setting = self.env['connector.setting'].sudo().search([
                            ('provider_id', '=', conn.id),
                            ('code', '=', 'tmn_code')
                        ], limit=1)
                        if setting:
                            setting.value = vals['vnpay_tmn_code']
                    if 'vnpay_hash_secret' in vals and vals['vnpay_hash_secret']:
                        setting = self.env['connector.setting'].sudo().search([
                            ('provider_id', '=', conn.id),
                            ('code', '=', 'hash_secret')
                        ], limit=1)
                        if setting:
                            setting.value = vals['vnpay_hash_secret']
        return res
