from odoo import fields, api, models

class GardenTree(models.Model):
    _name = "garden.tree"
    _description = "Thông tin kỹ thuật cây trồng"

    code = fields.Char(string="Mã loại", required=True, help="Mã định danh cho loại cây")
    name = fields.Char(string="Tên", required=True, help="Tên thường gọi của cây")
    scientific_name = fields.Char(string="Tên khoa học", help="Tên khoa học của cây")
    image = fields.Binary(string="Hình ảnh", help="Hình ảnh minh họa cho cây trồng")
    description = fields.Text(string="Mô tả", help="Mô tả chi tiết về cây, đặc điểm sinh học...")
    document_ids = fields.Many2many("knowledge.article", string="Tài liệu", help="Các tài liệu liên quan đến cây")
    note = fields.Text(string="Ghi chú", help="Các ghi chú khác về cây trồng")
    stage_ids = fields.Many2many("garden.stage", string="Giai đoạn", help="Các giai đoạn phát triển của cây")

    # Thông tin kỹ thuật tập trung vào đặc tính sinh học
    life_cycle = fields.Selection(
        [('annual', 'Hàng năm'), ('biennial', 'Hai năm'), ('perennial', 'Lâu năm')],
        string="Vòng đời", help="Vòng đời của cây"
    )
    sunlight = fields.Selection(
        [('full_sun', 'Đầy nắng'), ('partial_sun', 'Nắng một phần'), ('shade', 'Bóng râm')],
        string="Ánh sáng", help="Yêu cầu về ánh sáng của cây"
    )
    water_requirement = fields.Selection(
        [('low', 'Ít'), ('medium', 'Trung bình'), ('high', 'Nhiều')],
        string="Nước", help="Yêu cầu về lượng nước của cây"
    )
    soil_type = fields.Char(string="Loại đất", help="Loại đất phù hợp cho cây")

    # Thông tin về kích thước và hình thái
    mature_height = fields.Float(string="Chiều cao tối đa (m)", help="Chiều cao tối đa khi trưởng thành (mét)")
    mature_width = fields.Float(string="Đường kính tán tối đa (m)", help="Đường kính tán tối đa khi trưởng thành (mét)")
    leaf_type = fields.Char(string="Loại lá", help="Mô tả hình dạng, đặc điểm của lá")
    flower_color = fields.Char(string="Màu hoa", help="Màu sắc của hoa")
    fruit_type = fields.Char(string="Loại quả", help="Mô tả đặc điểm của quả (nếu có)")

    # Các trường thông tin khác
    growth_rate = fields.Char(string="Tốc độ sinh trưởng", help="Tốc độ sinh trưởng của cây (nhanh, chậm)")
    propagation_method = fields.Char(string="Phương pháp nhân giống", help="Các phương pháp nhân giống (hạt, giâm cành...)")
    resistance = fields.Char(string="Khả năng kháng bệnh", help="Khả năng kháng bệnh của cây")

    @api.model
    def create(self, vals):
        if 'code' not in vals or not vals['code']:
            vals['code'] = self.env['ir.sequence'].next_by_code('garden.tree') or '/'
        return super(GardenTree, self).create(vals)
