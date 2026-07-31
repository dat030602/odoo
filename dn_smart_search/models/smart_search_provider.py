from odoo import api, models


class SmartSearchProvider(models.AbstractModel):
    _name = "smart.search.provider"
    _description = "Smart Search Provider"

    @api.model
    def search(self, keyword, limit=20):
        return []

