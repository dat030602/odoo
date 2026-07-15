from odoo import api, fields, models,_
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    def simple_vat_check(self, country_code, vat_number):
        """
        Override: Chấp nhận MST/CCCD Việt Nam (số thuần chữ số 9-13 ký tự)
        mà không cần prefix quốc gia (VN...).
        Odoo standard gọi hàm này để kiểm tra định dạng VAT từng quốc gia.
        """
        import re
        # Nếu là số CCCD hoặc MST VN (9-13 chữ số thuần túy) → bỏ qua validate quốc tế
        if vat_number and re.match(r'^\d{9,13}$', vat_number.strip()):
            return True
        return super(ResPartner, self).simple_vat_check(country_code, vat_number)


    type_contact_id = fields.Many2one('res.partner.account', required=False) # remove
    type_contact_ids = fields.Many2many('res.partner.account', 'res_partner_type_contract_rel', 'partner_id', 'type_id', 'Contact Type', required=True)
    sales_team_captain_id = fields.Many2one('res.users','Sales Team Captain', related="team_id.user_id", store=True)
    sales_assistant_ids = fields.Many2many('res.users','res_sale_assistant_ids','sale_id','assisng_id','Sales Assistant', store=True, related="team_id.sales_assistant_ids")
    is_user_contact = fields.Boolean('Is The User Contact?', readonly=True, default=False)
    is_hide_fields = fields.Boolean(string="Is hide fields", compute="_compute_is_hide_fields", store=False)

    def get_hide_fields(self):
        for record in self:
            if record.is_user_contact:
                if record.env.user.partner_id.id == record.id:
                    return False
                else:
                    return not (self.env.user.has_group("biz_ccv_account.group_see_internal_contact")) and record.is_user_contact
            else:
                return False

    def _compute_is_hide_fields(self):
        for record in self:
            if record.is_user_contact:
                if record.env.user.partner_id.id == record.id:
                    record.is_hide_fields = False
                else:
                    record.is_hide_fields = not (self.env.user.has_group("biz_ccv_account.group_see_internal_contact")) and record.is_user_contact
            else:
                record.is_hide_fields = False

    def _update_log_history(self, old_values, new_values):
        Field = self.env['ir.model.fields'].sudo().with_context(active_test=False)
        self = self.with_context(lang=self.env.user.lang)
        context = self._context
        for res in self:
            check = False
            check_street = False
            skip_log=False
            msg = "<ul class='o_Message_trackingValues mb-0 ps-4'>"
            for old, val in old_values[res.id].items():
                # if old == 'street' or old == 'street2' or old == 'city' or old == 'stage' or old == 'country_id' or old == 'zip':
                if old in ['street', 'state_id', 'district_id','wards_id', 'country_id']:
                    check_street = True
            for old, val in old_values[res.id].items():
                field_id = Field._get('res.partner', old)
                if check_street:
                    if old == 'partner_latitude' or old == 'partner_longitude':
                        continue
                if val != new_values[res.id][old]:
                    check = True
                    if field_id.ttype == 'binary':
                        msg += "<li>\
                        <span class='o_TrackingValue_oldValue me-1 px-1 text-muted fw-bold fst-italic'>%s</span> \
                        <br/>" % ('Ảnh avatar của bạn đã bị chỉnh sửa')
                    else:
                        if context.get('skip_create_nolog') and old in ('partner_latitude', 'partner_longitude'):
                            skip_log = True

                        msg += "<li>\
                        <span class='o_TrackingValue_oldValue me-1 px-1 text-muted fw-bold fst-italic'>%s</span> -> \
                        <span class='o_TrackingValue_newValue me-1 fw-bold text-info'>%s</span>\
                        <span class='o_TrackingValue_fieldName ms-1 fst-italic text-muted'>(%s)</span>\
                        <br/>" % (val, new_values[res.id][old], field_id.field_description)
                        
            msg += "</ul>"
            if check:
                try:
                    res.message_post(body=msg, skip=skip_log)
                except Exception as e:
                    pass
                except ValueError as e:
                    pass

    @api.model_create_multi
    def create(self, vals):
        partner =  super(ResPartner,self).create(vals)
        for res in partner:
            if res.type_contact_ids:
                if any(type_contact not in self.env.user.type_contact_user_ids for type_contact in res.type_contact_ids):
                    raise UserError(_("You are not allowed to add delete this type of contact"))

        return partner

    def write(self, values):
        self = self.with_context(lang=self.env.user.lang)
        Field = self.env['ir.model.fields'].sudo().with_context(active_test=False)
        old_values = {}
        if 'type_contact_ids' in values:
            old_type_contact_dict = {partner.id : partner.type_contact_ids for partner in self}

        for res in self:
            old_values[res.id] = {}
            for val in values:
                if val not in ['is_company']:
                    field_id = Field._get('res.partner', val)
                    if field_id.tracking == 0 and field_id.store:
                        if field_id.ttype in ['many2many','one2many']:
                            old_values[res.id][val] = res[val] and ', '.join(res[val].mapped('display_name')) or _('None')
                        elif field_id.ttype == 'many2one':
                            old_values[res.id][val] = res[val] and res[val].display_name or _('None')
                        elif field_id.ttype  == 'selection':
                            old_values[res.id][val] = res[val] and dict(res._fields[val]._description_selection(res.env))[res[val]] or _('None')
                        else:
                            old_values[res.id][val] = res[val] or _('None')

        partner = super(ResPartner, self).write(values)
        new_values = {}
        for res in self:
            new_values[res.id] = {}
            for val in values:
                field_id = Field._get('res.partner', val)
                if val not in ['is_company']:
                    if field_id.tracking == 0 and field_id.store:
                        if field_id.ttype in ['many2many','one2many']:
                            new_values[res.id][val] = res[val] and ', '.join(res[val].mapped('display_name')) or _('None')
                        elif field_id.ttype == 'many2one':
                            new_values[res.id][val] = res[val] and res[val].display_name or _('None')
                        elif field_id.ttype  == 'selection':
                            new_values[res.id][val] = res[val] and dict(res._fields[val]._description_selection(res.env))[res[val]] or _('None')
                        else:
                            new_values[res.id][val] = res[val] or _('None')
        self._update_log_history(old_values,new_values)
        
        if 'type_contact_ids' in values:
            for partner in self:
                old_type_contact_ids = old_type_contact_dict.get(partner.id)
                add_type_contact = partner.type_contact_ids - old_type_contact_ids
                remove_type_contact = old_type_contact_ids - partner.type_contact_ids
                if (add_type_contact and add_type_contact not in self.env.user.type_contact_user_ids) or (remove_type_contact and remove_type_contact not in self.env.user.type_contact_user_ids):
                    raise UserError(_("You are not allowed to add delete this type of contact"))
        
        return partner

    def _cron_update_contact_type(self):
        partners = self.search([])
        for partner in partners:
            partner.write({
                'type_contact_ids': [(6,0, partner.type_contact_id.ids)]
            })


class ResPartnerAccount(models.Model):
    _name = "res.partner.account"
    _rec_name ='type_contact_name'
    _description = 'Partner account'

    type_contact_name = fields.Char(string='Type Contact Name')
    code_type_contact = fields.Char(string='Type Contact Code')

    # Special
    active = fields.Boolean(string="Active", default=True)