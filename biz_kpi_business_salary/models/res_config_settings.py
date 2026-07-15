from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Danh sách nhân viên áp dụng hoa hồng phòng kinh doanh
    sales_commission_employee_ids = fields.Many2many(
        'hr.employee',
        'config_sales_commission_employee_rel',
        'config_id',
        'employee_id',
        string='Nhân viên áp dụng hoa hồng phòng kinh doanh',
        help='Danh sách nhân viên được áp dụng tính hoa hồng phòng kinh doanh'
    )
    
    
    # Danh sách nhân viên bị loại trừ
    excluded_employee_ids = fields.Many2many(
        'hr.employee',
        'config_excluded_employee_rel',
        'config_id',
        'employee_id',
        string='Nhân viên bị loại trừ',
        help='Danh sách nhân viên bị loại trừ khỏi tính toán hoa hồng và thưởng'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()
        
        # Lấy danh sách nhân viên từ config parameter
        employee_ids_str = config.get_param('biz_kpi_business_salary.sales_commission_employee_ids', '[]')
        try:
            employee_ids = eval(employee_ids_str) if employee_ids_str and isinstance(employee_ids_str, str) else []
        except (ValueError, SyntaxError):
            employee_ids = []
        
        
        # Lấy danh sách nhân viên bị loại trừ từ config parameter
        excluded_ids_str = config.get_param('biz_kpi_business_salary.excluded_employee_ids', '[]')
        try:
            excluded_ids = eval(excluded_ids_str) if excluded_ids_str and isinstance(excluded_ids_str, str) else []
        except (ValueError, SyntaxError):
            excluded_ids = []
        
        res.update(
            sales_commission_employee_ids=[(6, 0, employee_ids)],
            excluded_employee_ids=[(6, 0, excluded_ids)]
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        config = self.env['ir.config_parameter'].sudo()
        
        # Lưu danh sách nhân viên vào config parameter
        employee_ids = self.sales_commission_employee_ids.ids
        config.set_param('biz_kpi_business_salary.sales_commission_employee_ids', str(employee_ids))
        
        
        # Lưu danh sách nhân viên bị loại trừ vào config parameter
        excluded_ids = self.excluded_employee_ids.ids
        config.set_param('biz_kpi_business_salary.excluded_employee_ids', str(excluded_ids))

    @api.model
    def get_excluded_employee_ids(self):
        """Lấy danh sách ID nhân viên bị loại trừ từ config parameter"""
        config = self.env['ir.config_parameter'].sudo()
        excluded_ids_str = config.get_param('biz_kpi_business_salary.excluded_employee_ids', '[]')
        try:
            excluded_ids = eval(excluded_ids_str) if excluded_ids_str and isinstance(excluded_ids_str, str) else []
        except (ValueError, SyntaxError):
            excluded_ids = []
        return excluded_ids

