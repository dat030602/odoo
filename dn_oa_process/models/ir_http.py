# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        # Expose the list of models that have an active validation process so the
        # web client can lock a form the instant it starts loading (onWillStart),
        # before any RPC and before the user can click anything.
        try:
            fp = self.env['fal.vprocess']
            result['vprocess_models'] = fp.vprocess_models()
            # Static config preloaded so the client needs no RPC to build the
            # process cache on refresh (the slow cold-start path).
            result['vprocess_bootstrap'] = fp.vprocess_bootstrap()
        except Exception:
            result['vprocess_models'] = []
            result['vprocess_bootstrap'] = {}
        return result
