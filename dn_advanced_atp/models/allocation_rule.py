from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AllocationRule(models.Model):
    _name = 'allocation.rule'
    _description = 'Allocation Rule'
    
    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    product_category_ids = fields.Many2many('product.category', string='Product Categories')
    line_ids = fields.One2many('allocation.rule.line', 'rule_id', string='Criteria')
    tie_breaker = fields.Selection([
        ('sale_date', 'Sale Date'),
        ('picking_id', 'Picking ID')
    ], string='Tie Breaker', default='sale_date')
    protect_started_picking = fields.Boolean(string='Protect Started Pickings', default=True)

    def _score(self, move):
        score = 0.0
        for line in self.line_ids:
            if line.criterion == 'partner_tag' and move.picking_id.partner_id.category_id:
                if line.partner_tag_id in move.picking_id.partner_id.category_id:
                    score += line.weight
            elif line.criterion == 'priority_flag':
                if move.picking_id.priority == '1':
                    score += line.weight
        return score

class AllocationRuleLine(models.Model):
    _name = 'allocation.rule.line'
    _description = 'Allocation Rule Line'

    rule_id = fields.Many2one('allocation.rule', required=True, ondelete='cascade')
    criterion = fields.Selection([
        ('partner_tag', 'Partner Tag'),
        ('delivery_date', 'Delivery Date'),
        ('order_date', 'Order Date'),
        ('order_amount', 'Order Amount'),
        ('priority_flag', 'Priority Flag')
    ], required=True)
    weight = fields.Integer(string='Weight', required=True)
    partner_tag_id = fields.Many2one('res.partner.category', string='Partner Tag')
    direction = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending')
    ], default='asc')
