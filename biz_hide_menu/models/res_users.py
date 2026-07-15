# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command


class Users(models.Model):
    """ User class. A res.users record models an OpenERP user and is different
        from an employee.

        res.users class now inherits from res.partner. The partner model is
        used to store the data related to the partner: lang, name, address,
        avatar, ... The user model is now dedicated to technical data.
    """
    _inherit = "res.users"

    hide_menu_access_ids = fields.Many2many(comodel_name='ir.ui.menu', relation='ir_ui_hide_menu_rel', column1='uid', column2='menu_id',
                                            string='Hide Access Menu')
