from odoo import fields, api, models

class GardenFertilizer(models.Model):
    _name = "garden.fertilizer"
    _description = "Thông tin kỹ thuật phân bón"

    code = fields.Char(string="Mã phân bón", required=True, help="Mã định danh cho loại phân bón")
    name = fields.Char(string="Tên phân bón", required=True, help="Tên thường gọi của phân bón")
    fertilizer_type = fields.Selection(
        [('organic', 'Hữu cơ'), ('inorganic', 'Vô cơ'), ('bio', 'Sinh học')],
        string="Loại phân bón", help="Phân loại phân bón"
    )
    form = fields.Selection(
        [('solid', 'Rắn'), ('liquid', 'Lỏng'), ('granular', 'Hạt')],
        string="Dạng", help="Dạng của phân bón"
    )
    uom_id = fields.Many2one('uom.uom', string="Đơn vị đo lường", help="Đơn vị đo lường của phân bón",
        domain=lambda self: '%s' % [('category_id', '=', int(self.env.ref('garden_management.garden_management_uom_category_id_fer').sudo().value))]
    )
    description = fields.Text(string="Mô tả", help="Mô tả chi tiết về phân bón")
    document_ids = fields.Many2many("knowledge.article", string="Tài liệu", help="Các tài liệu liên quan đến phân bón")
    note = fields.Text(string="Ghi chú", help="Các ghi chú khác về phân bón")
    
    # Thành phần chính
    npk_ratio = fields.Char(string="Tỷ lệ NPK", help="Tỷ lệ Nitrogen (N), Phosphorus (P), Potassium (K)")
    nutrient_content = fields.Text(string="Thành phần dinh dưỡng", help="Liệt kê chi tiết các thành phần dinh dưỡng")
    
    # Thông tin kỹ thuật
    application_method = fields.Char(string="Cách sử dụng", help="Hướng dẫn cách sử dụng")
    storage_conditions = fields.Char(string="Điều kiện bảo quản", help="Hướng dẫn điều kiện bảo quản")
    ph_level = fields.Float(string="Độ pH", help="Độ pH của phân bón")
    
    # Thông tin khác
    manufacturer = fields.Char(string="Nhà sản xuất", help="Nhà sản xuất phân bón")
    usage_notes = fields.Text(string="Lưu ý sử dụng", help="Các lưu ý khi sử dụng phân bón")

