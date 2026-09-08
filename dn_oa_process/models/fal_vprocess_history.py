# -*- coding: utf-8 -*-
from odoo import fields, models


class FalVprocessHistory(models.Model):
    _name = "fal.vprocess.history"
    _description = "Validation Process History"
    _order = "id desc"

    process_id = fields.Many2one("fal.vprocess", required=True, index=True, ondelete="cascade")
    execution_id = fields.Many2one(
        "fal.vprocess.execution", required=True, index=True, ondelete="cascade"
    )
    process_model = fields.Char(related="process_id.model_name", store=True, index=True)
    target = fields.Integer(required=True, index=True)
    action = fields.Selection(
        [
            ("start", "Start"),
            ("confirm", "Approve"),
            ("cancel", "Cancel"),
            ("back", "Back"),
            ("restart", "Restart"),
        ],
        required=True,
    )
    from_step_id = fields.Many2one("fal.vprocess.step", ondelete="set null")
    to_step_id = fields.Many2one("fal.vprocess.step", ondelete="set null")
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    note = fields.Char()
