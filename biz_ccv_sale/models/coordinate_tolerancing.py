from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

class CoordinateTolerancing(models.Model):
    _name = 'coordinate.tolerancing'
    _description = 'Coordinate Tolerancing'
    _rec_name = "allow_value"
    

    allow_value = fields.Float('Allow Value(m)', default=0.0, required=True)
    is_valid = fields.Boolean('Is Valid', default=False)
    

    @api.constrains('is_valid')
    def _validate_is_valid(self):
        count = self.search_count([('is_valid','!=', False)])
        if count > 1:
            raise ValidationError(_('Is Valid must be unique!'))


    _sql_constraints = [
        ('allow_value', 'unique (allow_value)', 'Allow Value(m) must be unique!')
    ]