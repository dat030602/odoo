from odoo import _, models, fields, api


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    qty_approved = fields.Float(string='Số lượng đã đề xuất', compute='_compute_qty_approved', store=True)

    @api.depends('quantity','approval_request_id')
    def _compute_qty_approved(self):
        for record in self:
            qty_approved = 0
            if record.product_id and record.approval_request_id.date:
                # Lấy tất cả product lines có cùng product_id và approval_request_id.date <= ngày hiện tại của request này, trạng thái approved
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('approval_request_id.request_status', '=', 'approved'),
                    ('approval_request_id.date', '<=', record.approval_request_id.date),
                ]
                lines = self.env['approval.product.line'].search(domain)
                qty_approved = sum(line.quantity for line in lines)
            record.qty_approved = qty_approved

    def action_open_product_request_history(self):
        self.ensure_one()
        if not self.product_id:
            return False

        tree_view = self.env.ref('ccv_approval_history.approval_request_tree_popup')
        form_view = self.env.ref('approvals.approval_request_view_form')

        context = dict(self.env.context or {})
        context.update({
            'search_default_product_id': self.product_id.id,
            'active_product_id': self.product_id.id,
        })

        domain = [('product_line_ids.product_id', '=', self.product_id.id)]
        if self.company_id:
            domain = ['&', ('company_id', '=', self.company_id.id)] + domain

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Approval History'),
            'res_model': 'approval.request',
            'views': [
                (tree_view.id, 'tree'),
                (form_view.id, 'form'),
            ],
            'view_mode': 'tree,form',
            'target': 'new',
            'domain': domain,
            'context': context,
        }

