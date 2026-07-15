# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def unlink(self):
        if not self:
            return True
        for record in self:
            current_user = self.env.user
            if not current_user.has_group("biz_ccv_account.group_delete_confirmed_order") and record.state not in ["draft"]:
                raise ValidationError(_("User does not have permission to delete this Quote/Order !"))
        return super(SaleOrder, self).unlink()