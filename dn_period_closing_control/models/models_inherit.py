from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PeriodLockMixin(models.AbstractModel):
    _name = 'period.lock.mixin'
    _description = 'Period Lock Mixin'

    def _check_period_lock_vals(self, vals_list, operation, date_field, scope):
        if self.env.context.get('bypass_period_lock'):
            return
            
        company_id = self.env.company.id
        lock = self.env['period.lock'].search([('company_id', '=', company_id), ('active', '=', True)], limit=1)
        if not lock:
            return
            
        line = lock.line_ids.filtered(lambda l: l.scope == scope)
        if not line or not line.lock_date:
            return
            
        if self.env.is_admin() and not line.applies_to_admin:
            return
            
        for vals in vals_list:
            if date_field in vals:
                record_date = fields.Date.to_date(vals[date_field])
                if record_date and record_date <= line.lock_date:
                    self._enforce_lock(scope, record_date, line.lock_date, operation, None, vals)

    def _check_period_lock(self, records, operation, date_field, scope, vals=None):
        if self.env.context.get('bypass_period_lock'):
            return
            
        company_id = self.env.company.id
        lock = self.env['period.lock'].search([('company_id', '=', company_id), ('active', '=', True)], limit=1)
        if not lock:
            return
            
        line = lock.line_ids.filtered(lambda l: l.scope == scope)
        if not line or not line.lock_date:
            return
            
        if self.env.is_admin() and not line.applies_to_admin:
            return
            
        for record in records:
            # Check old date
            old_date = getattr(record, date_field)
            if old_date and fields.Date.to_date(old_date) <= line.lock_date:
                self._enforce_lock(scope, old_date, line.lock_date, operation, record, vals)
                
            # Check new date
            if vals and date_field in vals:
                new_date = fields.Date.to_date(vals[date_field])
                if new_date and new_date <= line.lock_date:
                    self._enforce_lock(scope, new_date, line.lock_date, operation, record, vals)

    def _enforce_lock(self, scope, record_date, lock_date, operation, record, vals):
        # Check for active grant
        domain = [
            ('requester_id', '=', self.env.user.id),
            ('scope', '=', scope),
            ('state', '=', 'approved'),
            ('grant_start', '<=', fields.Datetime.now()),
            ('grant_end', '>=', fields.Datetime.now())
        ]
        if record:
            domain_with_res = domain + [('res_model', '=', record._name), ('res_id', '=', record.id)]
            request = self.env['period.unlock.request'].search(domain_with_res, limit=1)
            if not request:
                request = self.env['period.unlock.request'].search(domain + [('res_model', '=', False)], limit=1)
        else:
            request = self.env['period.unlock.request'].search(domain + [('res_model', '=', False)], limit=1)
            
        if request:
            # Log it
            self.env['period.unlock.log'].create({
                'request_id': request.id,
                'res_model': record._name if record else self._name,
                'res_id': record.id if record else 0,
                'operation': operation,
                'values_before': str(record.read()[0]) if record else '',
                'values_after': str(vals) if vals else '',
                'user_id': self.env.user.id
            })
            return
            
        raise UserError(_("Operation in locked period for %s. Lock date: %s") % (scope, lock_date))


class SaleOrder(models.Model):
    _inherit = ['sale.order', 'period.lock.mixin']
    _name = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        self._check_period_lock_vals(vals_list, 'create', date_field='date_order', scope='sale')
        return super().create(vals_list)

    def write(self, vals):
        self._check_period_lock(self, 'write', date_field='date_order', scope='sale', vals=vals)
        return super().write(vals)

    def unlink(self):
        self._check_period_lock(self, 'unlink', date_field='date_order', scope='sale')
        return super().unlink()

class StockMove(models.Model):
    _inherit = ['stock.move', 'period.lock.mixin']
    _name = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        self._check_period_lock_vals(vals_list, 'create', date_field='date', scope='inventory')
        return super().create(vals_list)

    def write(self, vals):
        self._check_period_lock(self, 'write', date_field='date', scope='inventory', vals=vals)
        return super().write(vals)

    def unlink(self):
        self._check_period_lock(self, 'unlink', date_field='date', scope='inventory')
        return super().unlink()
