# DEV DOC: Excel Report Definition Builder
### Module: `dn_excel_report_definition_builder` — kế thừa `dn_excel_report_definition_builder`, Odoo 19

---

## 1. Cấu trúc module

```
dn_excel_report_definition_builder/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── excel_report_definition.py
│   └── excel_report_definition_field.py
├── security/
│   ├── excel_report_security.xml       ← group riêng, KHÔNG dùng base.group_system trực tiếp
│   └── ir.model.access.csv
├── views/
│   └── excel_report_definition_views.xml
└── data/
    └── ir_sequence_data.xml (nếu cần đặt tên gợi nhớ tự động)
```

### `__manifest__.py`

```python
{
    'name': 'Excel Report Definition Builder',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'No-code builder: model + field + view + server action cho báo cáo Excel',
    'depends': ['dn_excel_report_definition_builder'],
    'data': [
        'security/excel_report_security.xml',
        'security/ir.model.access.csv',
        'views/excel_report_definition_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

---

## 2. Model `excel.report.definition`

```python
# models/excel_report_definition.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ExcelReportDefinition(models.Model):
    _name = 'excel.report.definition'
    _description = 'Excel Report Definition (No-code Builder)'

    name = fields.Char(required=True)

    # --- Target model -------------------------------------------------
    target_model_id = fields.Many2one(
        'ir.model', string='Target Model',
        help="Chọn model có sẵn, hoặc tạo model mới ngay tại đây "
             "(mặc định model mới luôn là Transient).")
    target_model_is_new = fields.Boolean(
        compute='_compute_target_model_is_new', store=True,
        help="True nếu model này được TẠO bởi chính record này. "
             "Dùng để quyết định có được auto-generate view hay không.")

    # Field dùng khi user gõ tên model mới (chưa có trong ir.model)
    new_model_name = fields.Char(string='New Model Display Name')
    new_model_technical_name = fields.Char(
        string='New Model Technical Name',
        help="VD: x_report_sale_filter. Tool tự thêm prefix x_ nếu thiếu.")

    field_ids = fields.One2many(
        'excel.report.definition.field', 'definition_id', string='Fields')

    # --- Server action --------------------------------------------------
    server_action_id = fields.Many2one(
        'ir.actions.server', string='Server Action',
        domain=[('state', '=', 'excel_template')],
        help="Server action loại 'Generate Excel From Template' "
             "(xem dn_excel_report_definition_builder, mục 10).")
    code = fields.Text(
        related='server_action_id.code', readonly=False,
        help="Sửa trực tiếp code của server action liên kết — "
             "KHÔNG lưu bản sao, không có bước đồng bộ.")

    # --- Trigger ----------------------------------------------------
    trigger_type = fields.Selection(
        [('menu', 'Menu'), ('contextual', 'Contextual Action')],
        default='menu', required=True)
    menu_id = fields.Many2one('ir.ui.menu', readonly=True, copy=False)
    menu_parent_id = fields.Many2one(
        'ir.ui.menu', string='Parent Menu',
        help="Chỉ dùng khi trigger_type = menu.")

    generated_view_id = fields.Many2one(
        'ir.ui.view', readonly=True, copy=False,
        help="View form được tool tự sinh. Rỗng nếu model đã có view "
             "từ trước (tool không đụng vào).")

    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft', required=True, copy=False)

    # --- Compute ---------------------------------------------------
    @api.depends('target_model_id')
    def _compute_target_model_is_new(self):
        # được set thật trong action_confirm(); ở đây chỉ giữ giá trị
        # đã lưu, tránh việc đổi target_model_id sau confirm làm sai lệch
        for rec in self:
            if not rec.target_model_id:
                rec.target_model_is_new = False

    # --- Constraints -------------------------------------------------
    @api.constrains('target_model_id', 'new_model_technical_name')
    def _check_target_model(self):
        for rec in self:
            if not rec.target_model_id and not rec.new_model_technical_name:
                raise ValidationError(_(
                    "Chọn model có sẵn hoặc nhập tên model mới."))

    # --- Actions -------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()
        if self.state == 'confirmed':
            return
        if not self.server_action_id:
            raise UserError(_(
                "Vui lòng chọn hoặc tạo Server Action trước khi Confirm."))

        self._ensure_target_model()
        self._create_fields()
        self._maybe_generate_view()
        self._setup_trigger()

        self.state = 'confirmed'

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'

    # --- Private pipeline steps -----------------------------------
    def _ensure_target_model(self):
        self.ensure_one()
        if self.target_model_id:
            return

        technical_name = self.new_model_technical_name or ''
        if not technical_name.startswith('x_'):
            technical_name = 'x_' + technical_name

        model = self.env['ir.model'].create({
            'name': self.new_model_name or self.name,
            'model': technical_name,
            'transient': True,          # ← default theo quyết định đã chốt
            'state': 'manual',
        })
        self.target_model_id = model.id
        self.target_model_is_new = True
        # registry cần reload để model mới usable ngay trong transaction này
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr)

    def _create_fields(self):
        self.ensure_one()
        Fields = self.env['ir.model.fields']
        for line in self.field_ids:
            technical_name = line.field_technical_name
            if not technical_name.startswith('x_'):
                technical_name = 'x_' + technical_name

            existing = Fields.search([
                ('model_id', '=', self.target_model_id.id),
                ('name', '=', technical_name),
            ], limit=1)
            if existing:
                continue  # bỏ qua field trùng, không raise lỗi cứng

            vals = {
                'model_id': self.target_model_id.id,
                'name': technical_name,
                'field_description': line.field_label,
                'ttype': line.field_type,
                'required': line.required,
                'state': 'manual',
            }
            if line.field_type == 'many2one':
                if not line.relation_model_id:
                    raise UserError(_(
                        "Field '%s' kiểu Many2one cần chọn Relation Model."
                    ) % line.field_label)
                vals['relation'] = line.relation_model_id.model
            if line.field_type == 'selection':
                vals['selection'] = line.selection_value_text or "[]"

            Fields.create(vals)

        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr)

    def _maybe_generate_view(self):
        self.ensure_one()
        if not self.target_model_is_new:
            return  # model có sẵn → không đụng view, theo spec mục 4
        if self.generated_view_id:
            return  # đã generate ở lần confirm trước (an toàn nếu gọi lại)

        model_name = self.target_model_id.model
        existing_view = self.env['ir.ui.view'].search([
            ('model', '=', model_name),
            ('type', '=', 'form'),
        ], limit=1)
        if existing_view:
            return  # đã có view (ai đó tạo tay) → không ghi đè

        field_tags = ''.join(
            '<field name="%s"/>' % (
                f.field_technical_name if f.field_technical_name.startswith('x_')
                else 'x_' + f.field_technical_name
            )
            for f in self.field_ids
        )
        arch = (
            '<form string="%s">'
            '<sheet><group>%s</group></sheet>'
            '</form>'
        ) % (self.name, field_tags)

        view = self.env['ir.ui.view'].create({
            'name': '%s.form.auto' % model_name,
            'model': model_name,
            'type': 'form',
            'arch': arch,
        })
        self.generated_view_id = view.id

    def _setup_trigger(self):
        self.ensure_one()
        model_name = self.target_model_id.model

        if self.trigger_type == 'menu':
            if self.menu_id:
                return  # đã tạo từ trước
            menu = self.env['ir.ui.menu'].create({
                'name': self.name,
                'parent_id': self.menu_parent_id.id if self.menu_parent_id else False,
                'action': 'ir.actions.server,%d' % self.server_action_id.id,
            })
            self.menu_id = menu.id

        elif self.trigger_type == 'contextual':
            self.server_action_id.write({
                'binding_model_id': self.target_model_id.id,
                'binding_type': 'action',
                'binding_view_types': 'list,form',
            })
```

> **Lưu ý quan trọng — cần verify trước khi ship (đã nêu ở spec mục 8):**
> - `ir.ui.menu.action` là field kiểu Reference — cú pháp `'ir.actions.server,<id>'` là cách chuẩn để set Reference field bằng ORM `write`/`create`. Cần test tay để chắc chắn menu mở đúng ra server action (không qua `ir.actions.act_window`).
> - `binding_view_types` — giá trị hợp lệ trên Odoo 17+ là `'list'` (không phải `'tree'`). Cần test trên bản 19 cụ thể bạn đang dùng.
> - `env.registry.setup_models()` — API nội bộ có thể đổi tên/behaviour giữa các Odoo version; kiểm tra lại đúng cách "làm registry nhận model/field mới ngay trong cùng transaction" theo Odoo 19 (có thể cần `self.env.registry.init_models(...)` hoặc chỉ cần `_setup_fields`/`flush` tuỳ version — đây là điểm dễ lệch nhất giữa các bản Odoo, nên test kỹ).

---

## 3. Model `excel.report.definition.field`

```python
# models/excel_report_definition_field.py
from odoo import fields, models


class ExcelReportDefinitionField(models.Model):
    _name = 'excel.report.definition.field'
    _description = 'Excel Report Definition — Field Line'

    definition_id = fields.Many2one(
        'excel.report.definition', required=True, ondelete='cascade')

    field_label = fields.Char(required=True)
    field_technical_name = fields.Char(
        required=True,
        help="Không cần gõ prefix x_, tool tự thêm nếu thiếu.")
    field_type = fields.Selection([
        ('char', 'Text'),
        ('text', 'Long Text'),
        ('integer', 'Integer'),
        ('float', 'Decimal'),
        ('boolean', 'Checkbox'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('many2one', 'Many2one'),
        ('selection', 'Selection'),
    ], required=True, default='char')

    relation_model_id = fields.Many2one(
        'ir.model', string='Relation Model',
        help="Bắt buộc khi Field Type = Many2one.")
    selection_value_text = fields.Text(
        string='Selection Values',
        help="Mỗi dòng 1 giá trị dạng key:Label. "
             "Tool tự convert sang list Python khi tạo field.")
    required = fields.Boolean()
```

---

## 4. Security

```xml
<!-- security/excel_report_security.xml -->
<odoo>
    <record id="group_excel_report_builder" model="res.groups">
        <field name="name">Excel Report Builder / Manager</field>
        <field name="category_id" ref="base.module_category_technical"/>
    </record>
</odoo>
```

```csv
# security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_excel_report_definition,access.excel.report.definition,model_excel_report_definition,group_excel_report_builder,1,1,1,1
access_excel_report_definition_field,access.excel.report.definition.field,model_excel_report_definition_field,group_excel_report_builder,1,1,1,1
```

> Group riêng (không dùng thẳng `base.group_system`) để tách quyền "quản lý report builder" khỏi quyền hệ thống toàn cục — nhưng vì action Confirm ghi trực tiếp vào `ir.model`/`ir.model.fields`/`ir.ui.menu` (các model chỉ `base.group_system` mới có quyền ghi theo ACL gốc của Odoo), cần thêm 1 trong 2 cách:
> - Thêm user vào `base.group_system` ngoài group riêng này, **hoặc**
> - Dùng `sudo()` có kiểm soát trong `action_confirm()` (rủi ro cao hơn, chỉ nên làm nếu chắc chắn kiểm soát được input).
>
> Khuyến nghị: giữ cách 1 (require `base.group_system`), an toàn hơn cho MVP.

---

## 5. View XML

```xml
<!-- views/excel_report_definition_views.xml -->
<odoo>
    <record id="view_excel_report_definition_form" model="ir.ui.view">
        <field name="name">excel.report.definition.form</field>
        <field name="model">excel.report.definition</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_confirm" type="object"
                            string="Confirm" class="btn-primary"
                            invisible="state == 'confirmed'"/>
                    <button name="action_reset_draft" type="object"
                            string="Reset to Draft"
                            invisible="state == 'draft'"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button type="object" name="%(action_open_server_action)d"
                                class="oe_stat_button" icon="fa-cogs"
                                invisible="not server_action_id">
                            <div class="o_stat_info">
                                <span class="o_stat_text">Server Action</span>
                            </div>
                        </button>
                        <button type="object" name="%(action_open_generated_view)d"
                                class="oe_stat_button" icon="fa-eye"
                                invisible="not generated_view_id">
                            <div class="o_stat_info">
                                <span class="o_stat_text">View</span>
                            </div>
                        </button>
                    </div>

                    <group>
                        <field name="name"/>
                        <field name="target_model_id"
                               invisible="target_model_is_new"
                               readonly="state == 'confirmed'"/>
                        <field name="target_model_is_new" invisible="1"/>
                    </group>

                    <group string="New Model" invisible="target_model_id">
                        <field name="new_model_name"
                               readonly="state == 'confirmed'"/>
                        <field name="new_model_technical_name"
                               readonly="state == 'confirmed'"/>
                    </group>

                    <notebook>
                        <page string="Fields">
                            <field name="field_ids"
                                   readonly="state == 'confirmed'">
                                <list editable="bottom">
                                    <field name="field_label"/>
                                    <field name="field_technical_name"/>
                                    <field name="field_type"/>
                                    <field name="relation_model_id"
                                           column_invisible="parent.field_type != 'many2one'"/>
                                    <field name="required"/>
                                </list>
                            </field>
                        </page>

                        <page string="Server Action">
                            <group>
                                <field name="server_action_id"
                                       readonly="state == 'confirmed'"/>
                            </group>
                            <field name="code" widget="code"
                                   options="{'mode': 'python'}"/>
                        </page>

                        <page string="Trigger">
                            <group>
                                <field name="trigger_type"/>
                                <field name="menu_parent_id"
                                       invisible="trigger_type != 'menu'"/>
                                <field name="menu_id" readonly="1"
                                       invisible="not menu_id"/>
                            </group>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <record id="view_excel_report_definition_list" model="ir.ui.view">
        <field name="name">excel.report.definition.list</field>
        <field name="model">excel.report.definition</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <field name="target_model_id"/>
                <field name="trigger_type"/>
                <field name="state"/>
            </list>
        </field>
    </record>

    <record id="action_excel_report_definition" model="ir.actions.act_window">
        <field name="name">Excel Report Definitions</field>
        <field name="res_model">excel.report.definition</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_excel_report_definition_root"
              name="Excel Report Builder"
              parent="base.menu_custom"
              groups="dn_excel_report_definition_builder.group_excel_report_builder"/>
    <menuitem id="menu_excel_report_definition"
              name="Report Definitions"
              parent="menu_excel_report_definition_root"
              action="action_excel_report_definition"/>
</odoo>
```

**Smart button — 2 action window phụ trợ** (mở form của record liên kết,
điều hướng theo `res_id` runtime):

```xml
<record id="action_open_server_action" model="ir.actions.act_window">
    <field name="name">Server Action</field>
    <field name="res_model">ir.actions.server</field>
    <field name="view_mode">form</field>
    <field name="binding_type">action</field>
</record>

<record id="action_open_generated_view" model="ir.actions.act_window">
    <field name="name">View</field>
    <field name="res_model">ir.ui.view</field>
    <field name="view_mode">form</field>
    <field name="binding_type">action</field>
</record>
```

> Cách đơn giản hơn (khuyến nghị thay cho 2 action ở trên): dùng
> `type="object"` với method Python trả về `act_window` dict trỏ
> `res_id = self.server_action_id.id` / `self.generated_view_id.id`
> ngay trong model chính — tránh phải quản lý thêm 2 `ir.actions.act_window`
> tĩnh. Ví dụ:
>
> ```python
> def action_open_server_action(self):
>     self.ensure_one()
>     return {
>         'type': 'ir.actions.act_window',
>         'res_model': 'ir.actions.server',
>         'view_mode': 'form',
>         'res_id': self.server_action_id.id,
>         'target': 'current',
>     }
> ```
> Nếu chọn hướng này thì trong XML, nút smart button gọi thẳng
> `name="action_open_server_action" type="object"` thay vì
> `name="%(action_open_server_action)d"`.

---

## 6. Checklist verify trên Odoo 19 trước khi merge (nhắc lại có kèm cách test)

| # | Cần verify | Cách test nhanh (Odoo shell) |
|---|---|---|
| 1 | `ir.ui.menu.action` nhận Reference tới `ir.actions.server` | `env['ir.ui.menu'].create({'name': 'x', 'action': 'ir.actions.server,%d' % sa.id})` rồi mở menu, xem có chạy đúng action không |
| 2 | Giá trị hợp lệ của `binding_view_types` | Kiểm tra field definition: `env['ir.actions.server']._fields['binding_view_types'].selection` |
| 3 | Cách force registry nhận field/model mới trong cùng transaction | Test tạo `ir.model` + `ir.model.fields` rồi gọi ngay `env['x_model_moi'].create({...})` trong cùng shell session, xem có lỗi `KeyError` không |
| 4 | `ir.model.fields` field `selection` format string hợp lệ | Test tạo field selection với `selection = "[('a','A'),('b','B')]"` |

---

## 7. Ghi chú migration/nâng cấp module

- Khi upgrade module, **không** re-run `_ensure_target_model()` / `_create_fields()` cho record đã `state = confirmed` — các method này chỉ nên chạy qua `action_confirm()`, không đặt trong `data` XML hay `post_init_hook`.
- Nếu xoá record `excel.report.definition`, **không tự động xoá** `ir.model`/`ir.model.fields`/`ir.ui.menu` liên quan (dữ liệu người dùng có thể đã phát sinh trên model đó) — để user tự xoá thủ công qua Technical menu nếu chắc chắn an toàn. Có thể cân nhắc thêm nút "Cleanup" riêng ở phase sau, có confirm dialog rõ ràng cảnh báo mất dữ liệu.