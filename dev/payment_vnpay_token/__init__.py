# Part of Odoo. See LICENSE file for full copyright and licensing details.

def post_init_hook(env):
    """Post-installation hook for VNPay Token module."""
    # Set up default configuration
    env['ir.config_parameter'].sudo().set_param('payment_vnpay_token.ip_address', '127.0.0.1')

def uninstall_hook(env):
    """Uninstallation hook for VNPay Token module."""
    # Clean up configuration
    env['ir.config_parameter'].sudo().set_param('payment_vnpay_token.ip_address', '')

from . import models
from . import controllers