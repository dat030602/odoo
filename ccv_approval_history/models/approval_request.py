from odoo import _, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def action_open_request_product_lines(self):
        self.ensure_one()

        product_id = self.env.context.get('active_product_id')

        tree_view = self.env.ref('ccv_approval_history.approval_product_line_view_tree_popup')
        form_view = self.env.ref('approvals.approval_product_line_view_form')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Lines'),
            'res_model': 'approval.product.line',
            'view_mode': 'tree,form',
            'views': [
                (tree_view.id, 'tree'),
                (form_view.id, 'form'),
            ],
            'target': 'new',
            'domain': [('approval_request_id', '=', self.id), ('product_id', '=', product_id)],
            'context': {
                'default_approval_request_id': self.id,
            },
        }

