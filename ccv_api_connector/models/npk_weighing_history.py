from odoo import models, fields, api
import logging
import uuid
import requests
from odoo.exceptions import UserError
import datetime
import json
import ast

_logger = logging.getLogger(__name__)

def _parse_api_datetime(dt_str):
    if not dt_str or not isinstance(dt_str, str):
        return False
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return False

class NpkWeighingHistory(models.Model):
    """Model lưu trữ thông tin NPK Weighing History"""
    _name = 'npk.weighing.history'
    _description = 'NPK Weighing History'
    _order = 'stock_date_receipt desc, uom_id, production_id'

    # Link to MRP Production
    production_id = fields.Many2one('mrp.production', string="Lệnh sản xuất", ondelete='cascade')
    
    # Basic fields
    partner_ids = fields.Many2many('res.partner', string="Khách hàng", compute='_compute_production_id', store=True)
    product_id = fields.Many2one('product.product', string="Sản phẩm", compute='_compute_production_id', store=True)
    uom_id = fields.Many2one('uom.uom', string="Loại bao", compute='_compute_production_id', store=True)
    stock_date_receipt = fields.Datetime(string="Ngày nhập kho", compute='_compute_production_id', store=True)

    @api.depends('production_id')
    def _compute_production_id(self):
        for record in self:
            partner_ids = self.env['res.partner']
            product_id = self.env['product.product']
            uom_id = self.env['uom.uom']
            stock_date_receipt = False
            if record.production_id:
                partner_ids |= record.production_id.partner_ids
                product_id = record.production_id.product_id
                uom_id = record.production_id.product_id.default_specification_id
                stock_date_receipt = record.production_id.stock_date_receipt
            record.update({
                'partner_ids': partner_ids,
                'product_id': product_id,
                'uom_id': uom_id,
                'stock_date_receipt': stock_date_receipt
            })
    
    # API response fields
    api_id = fields.Char(string="ID API", copy=False)
    name = fields.Char(string="Số phiếu", copy=False)
    odoo_ticket_name = fields.Char(string="Số phiếu Odoo", copy=False)
    vehicle = fields.Char(string="Phương tiện", copy=False)
    factory_id = fields.Many2one('npk.weighing.factory', string="Nhà máy", copy=False, related='machine_id.factory_id')
    machine_id = fields.Many2one('npk.weighing.machine', string="Máy cân", copy=False)
    quantity_start = fields.Integer(string="Số lượng bắt đầu", copy=False)
    plan_counter = fields.Integer(string="Số lượng kế hoạch", copy=False)
    counter = fields.Integer(string="Số lượng", copy=False)
    total = fields.Float(string="Khối lượng", copy=False)
    create_time = fields.Datetime(string="Thời gian tạo", copy=False)
    start_time = fields.Datetime(string="Thời gian bắt đầu", copy=False)
    stop_time = fields.Datetime(string="Thời gian dừng", copy=False)
    last_time = fields.Datetime(string="Thời gian cuối", copy=False)
    batch_number = fields.Char(string="Số lô", copy=False)
    unit_price = fields.Float(string="Đơn giá", copy=False)
    note = fields.Text(string="Ghi chú", copy=False)
    is_finished = fields.Boolean(string="Đã hoàn thành", copy=False)
    is_deleted = fields.Boolean(string="Đã xóa", copy=False)

    def _get_api_base_url(self):
        """Get API base URL from system parameter"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('npk_weighing.api_host', '')
        if not base_url or not isinstance(base_url, str):
            raise UserError("Chưa cấu hình API host trong system parameter (npk_weighing.api_host)")
        return base_url.rstrip('/')

    def _get_api_key(self):
        """Get API key from system parameter"""
        return self.env['ir.config_parameter'].sudo().get_param('npk_weighing.api_key', '')

    def _execute_api_request(self, method, endpoint, payload=None, params=None):
        """
        Execute API request with given method, endpoint, and payload/params
        
        Args:
            method (str): HTTP method ('GET', 'POST', 'PUT', 'DELETE')
            endpoint (str): API endpoint path (e.g., '/api/App/GetData')
            payload (dict, optional): Request body for POST/PUT requests
            params (dict, optional): Query parameters for GET requests
            
        Returns:
            dict: API response data
        """
        base_url = self._get_api_base_url()
        url = f"{base_url}{endpoint}"
        
        method = method.upper()
        try:
            _logger.info(f"API request: {method} {url} {params} {payload}")
            if method == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=payload, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=payload, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Check if response has content
            response_text = response.text.strip()
            if not response_text:
                _logger.warning(f"API response is empty [{method} {url}]")
                return {}
            
            # Try to parse JSON
            try:
                response_data = response.json()
                _logger.info("API response: %s", json.dumps(response_data, indent=4, ensure_ascii=False))
                return response_data
            except ValueError as json_error:
                # Catch JSONDecodeError from both json and simplejson (requests uses simplejson)
                _logger.error(f"API response is not valid JSON [{method} {url}]: {json_error}")
                _logger.error(f"Raw response text: {response_text[:500]}")  # Log first 500 chars
                raise UserError(f"Phản hồi API không phải định dạng JSON hợp lệ: {str(json_error)}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"API request error [{method} {url}]: {e}")
            raise UserError(f"Lỗi khi gọi API: {str(e)}")

    def _fetch_factories(self):
        """Fetch list of factories"""
        return self._execute_api_request('GET', '/api/App/GetNhaMay')

    def _fetch_machines_by_factory(self, id):
        """Fetch list of machines by factory ID"""
        return self._execute_api_request('GET', f'/api/App/GetCan/{id}')

    def _fetch_running_tickets_by_machine(self, id):
        """Fetch running tickets by machine ID"""
        return self._execute_api_request('GET', f'/api/App/GetPhieuRun/{id}')

    def _fetch_ticket_by_number(self):
        """Fetch ticket by ticket number"""
        return self._execute_api_request('GET', f'/api/App/GetPhieu/{self.name}')

    def _update_history(self, result):
        # 1. Chỉ cập nhật máy cân nếu API có trả về mã cân hợp lệ
        id_can = result.get('IdCan')
        if id_can:
            machine_id = self.env['npk.weighing.machine'].search([('code', '=', str(id_can))], limit=1)
            if machine_id and machine_id != self.machine_id:
                self.machine_id = machine_id.id
                if self.production_id:
                    self.production_id.machine_id = machine_id.id

        vals = {}
        
        # Ánh xạ các trường từ API về trường Odoo
        mappings = {
            'Id': 'api_id',
            'PhuongTien': 'vehicle',
            'SoLo': 'batch_number',
            'DonGia': 'unit_price',
            'GhiChu': 'note',
            'IsDeleted': 'is_deleted',
            'SLBatDau': 'quantity_start',
            'PlanCounter': 'plan_counter',
        }
        
        for api_key, odoo_field in mappings.items():
            if api_key in result:
                vals[odoo_field] = result[api_key]
                
        # Ngăn chặn việc ghi đè số lượng và khối lượng cân về 0 hoặc nhỏ hơn khi đã có dữ liệu thực tế
        if 'Total' in result:
            new_total = float(result['Total'] or 0.0)
            if new_total > 0.0 or not self.total:
                vals['total'] = new_total
                
        if 'Counter' in result:
            new_counter = int(result['Counter'] or 0)
            if new_counter > 0 or not self.counter:
                vals['counter'] = new_counter
                
        # Xử lý trường IsFinished đặc thù để tránh bị ghi đè về False
        if 'IsFinished' in result:
            vals['is_finished'] = bool(result['IsFinished']) or self.is_finished

        # Xử lý các trường ngày tháng nếu có trong result
        datetime_mappings = {
            'CreateTime': 'create_time',
            'StartTime': 'start_time',
            'StopTime': 'stop_time',
            'LastTime': 'last_time',
        }
        for api_key, odoo_field in datetime_mappings.items():
            if api_key in result:
                vals[odoo_field] = _parse_api_datetime(result[api_key])

        # 2. Chỉ cập nhật Số phiếu nếu API trả về giá trị không rỗng
        new_name = result.get('SoPhieu')
        if new_name:
            vals['name'] = new_name

        if vals:
            self.write(vals)

    def _cron_update_history(self, cur_date=None):
        """Cron job to update weighing data"""
        if not cur_date:
            cur_date = datetime.date.today()
        from_date = datetime.datetime.combine(cur_date, datetime.time.min) - datetime.timedelta(hours=7)
        to_date = datetime.datetime.combine(cur_date, datetime.time.max) - datetime.timedelta(hours=7)
        histories = self.search([('stock_date_receipt', '>=', from_date.strftime('%Y-%m-%d %H:%M:%S')), ('stock_date_receipt', '<=', to_date.strftime('%Y-%m-%d %H:%M:%S'))])
        for history in histories:
            result = history._fetch_ticket_by_number()
            if result:
                history._update_history(result)

    def _fetch_weighing_data_by_ticket(self):
        """Fetch weighing data by ticket number"""
        return self._execute_api_request('GET', f'/api/App/GetData/{self.name}')
    
    def _prepare_weighing_data(self):
        """Prepare weighing data"""
        # Format current UTC time as ISO 8601 with Z timezone (e.g., 2025-11-04T08:23:23.531Z)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        return {
            "KhachHang": ','.join([str(abbreviation) for abbreviation in self.partner_ids.mapped('abbreviation') if abbreviation]),
            "SanPham": self.product_id.default_code or '',
            "TenSanPham": self.product_id.with_context(lang='vi_VN').name or '',
            "Idnm": self.factory_id.code or '',
            "IdCan": int(self.machine_id.code or ''),
            "PlanCounter": self.plan_counter or 0,
            "GhiChu": self.note or '',
            "Id": str(uuid.uuid4()),
            "Stt": 0,
            "SoPhieu": self.name or '',
            "PhuongTien": "",
            "SLBatDau": 0,
            "Counter": 0,
            "Total": 0,
            "CreateTime": current_time_str,
            "StartTime": current_time_str,
            "StopTime": current_time_str,
            "LastTime": current_time_str,
            "Solo": "",
            "DonGia": 0,
            "IsFinished": 0,
            "IsDeleted": 0,
            "TrongLuongBao": 1000 / (self.product_id.default_specification_id.factor or 1),
        }

    def _create_weighing_ticket(self):
        """Create new weighing ticket or sync if already exists on scale"""
        self.ensure_one()
        
        # 1. Đảm bảo bản ghi Odoo có tên phiếu (name)
        if not self.name:
            # Ưu tiên lấy theo tên Lệnh sản xuất nếu có
            prefix = self.production_id.name or f"MO-{self.id}"
            generated_name = f"{prefix}-{fields.Datetime.now().strftime('%H%M%S')}"
            
            # Lưu tên dài vào cả name (tạm thời) và odoo_ticket_name (vĩnh viễn)
            self.write({
                'name': generated_name,
                'odoo_ticket_name': generated_name
            })
            self.flush_recordset(['name', 'odoo_ticket_name'])

        # 2. Kiểm tra xem trên máy cân ĐÃ CÓ phiếu này chưa (Tránh tạo trùng khi nhấn đẩy nhiều lần)
        try:
            existing_ticket = self._fetch_ticket_by_number()
        except Exception:
            existing_ticket = False
        
        if existing_ticket:
            _logger.info(f"Ticket {self.name} already exists on machine. Syncing data instead of creating.")
            self._update_history(existing_ticket)
            return existing_ticket
        else:
            # 3. Nếu chưa có trên máy cân, thực hiện POST để tạo mới
            _logger.info(f"Ticket {self.name} not found on machine. Creating new ticket.")
            payload = self._prepare_weighing_data()
            res = self._execute_api_request('POST', '/api/App/InsPhieu', payload=payload)
            if res:
                self._update_history(res)
            return res

    def _create_weighing_list_ticket(self):
        """Create new weighing ticket"""
        payload = [rec._prepare_weighing_data() for rec in self]
        res = self._execute_api_request('POST', '/api/App/InsListPhieu', payload=payload)
        if res:
            for rec in res:
                line = self.filtered(lambda r: r.product_id.default_code == rec.get('SanPham', ''))
                line._update_history(rec)
        return res

    def action_check_status_weighing(self):
        """Kiểm tra trạng thái cân"""
        response = self._fetch_ticket_by_number()
        return self.action_open_weighing_ticket(response)

    def action_open_weighing_ticket(self, data):
        """Open weighing ticket"""
        action = self.env.ref('ccv_api_connector.action_check_request_api_wizard').sudo().read()[0]
        # Parse context string to dict if it's a string
        if isinstance(action.get('context'), str):
            context = ast.literal_eval(action.get('context', '{}'))
        else:
            context = action.get('context', {})
        
        # Update context with default values
        # List of datetime fields that need to be converted from ISO format
        datetime_fields = ['CreateTime', 'StartTime', 'StopTime', 'LastTime']
        
        # Trừ đi 7 tiếng
        keys = data.keys()
        for key in keys:
            value = data.get(key, False)
            # Nếu trường datetime thì trừ đi 7 tiếng so với giờ gốc (UTC-7)
            if key in datetime_fields and value:
                dt_value = _parse_api_datetime(value)
                if dt_value:
                    # Chuyển về kiểu datetime, trừ đi 7 tiếng, sau đó lại chuyển về str theo Odoo format
                    parsed_dt = datetime.datetime.strptime(dt_value, "%Y-%m-%d %H:%M:%S")
                    updated_dt = parsed_dt - datetime.timedelta(hours=7)
                    value = updated_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    value = value
            context[f'default_{key}'] = value
        
        # Add create/edit/delete flags to context
        context.update({
            'create': False,
            'edit': False,
            'delete': False
        })
        action['context'] = context
        return action
    
    @api.model
    def api_confirm_npk_weighing(self, ticket_name, ma_nha_may, ma_can, vals):
        # Hàm này để máy cân gọi vào Odoo
        record = self.search([('name', '=', ticket_name)], limit=1)
        if record:
            record._update_history(vals)
            # Ép trạng thái thành "Đã cân" (is_finished = True) để mrp.production cập nhật state_weighing
            record.is_finished = True
            
            # Lưu ngay dữ liệu xuống database để polling tự động nhận diện mà không cần reload
            self.env.flush_all()
            self.env.cr.commit()
            return True
        return False
