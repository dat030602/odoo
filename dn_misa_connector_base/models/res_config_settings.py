from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    misa_tax_code = fields.Char(related='company_id.misa_tax_code', readonly=False)
    misa_username = fields.Char(related='company_id.misa_username', readonly=False)
    misa_password = fields.Char(related='company_id.misa_password', readonly=False)
    misa_client_id = fields.Char(related='company_id.misa_client_id', readonly=False)
    misa_client_secret = fields.Char(related='company_id.misa_client_secret', readonly=False)
    misa_device_id = fields.Char(related='company_id.misa_device_id', readonly=False)
    misa_otp_code = fields.Char(related='company_id.misa_otp_code', readonly=False)

    misa_meinvoice_base_url = fields.Char(related='company_id.misa_meinvoice_base_url', readonly=False)
    misa_meinvoice_token_expiry = fields.Datetime(related='company_id.misa_meinvoice_token_expiry', readonly=True)

    misa_inbot_base_url = fields.Char(related='company_id.misa_inbot_base_url', readonly=False)
    misa_inbot_subscribers_id = fields.Char(related='company_id.misa_inbot_subscribers_id', readonly=False)
    misa_inbot_token_expiry = fields.Datetime(related='company_id.misa_inbot_token_expiry', readonly=True)

    def action_test_meinvoice_connection(self):
        return self.company_id.action_test_meinvoice_connection()

    def action_verify_meinvoice_2fa(self):
        return self.company_id.action_verify_meinvoice_2fa()

    def action_test_inbot_connection(self):
        return self.company_id.action_test_inbot_connection()

    def action_sync_inbot_subscribers_and_organizations(self):
        return self.company_id.action_sync_inbot_subscribers_and_organizations()
