from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import xml.etree.ElementTree as ET
import base64
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ImportXmlWizard(models.TransientModel):
    _name = 'import.xml.wizard'
    _description = 'Wizard import dữ liệu XML từ hóa đơn điện tử'

    xml_file = fields.Binary(string='File XML', required=True)
    xml_filename = fields.Char(string='Tên file')
    
    # Thống kê import
    total_invoices = fields.Integer(string='Tổng số hóa đơn', readonly=True)
    imported_invoices = fields.Integer(string='Hóa đơn đã import', readonly=True)
    skipped_invoices = fields.Integer(string='Hóa đơn bỏ qua', readonly=True)
    error_messages = fields.Text(string='Thông báo lỗi', readonly=True)

    def action_import_xml(self):
        """Import dữ liệu từ file XML"""
        if not self.xml_file:
            raise UserError(_('Vui lòng chọn file XML để import!'))

        try:
            # Decode file XML
            xml_content = base64.b64decode(self.xml_file).decode('utf-8')
            root = ET.fromstring(xml_content)
            
            imported_count = 0
            skipped_count = 0
            error_messages = []
            
            # Tìm tất cả các hóa đơn trong XML
            invoices = root.findall('.//HDon')
            
            self.total_invoices = len(invoices)
            
            for invoice in invoices:
                try:
                    self._import_single_invoice(invoice)
                    imported_count += 1
                except Exception as e:
                    skipped_count += 1
                    error_msg = f"Hóa đơn {invoice.find('.//SHDon').text if invoice.find('.//SHDon') is not None else 'Unknown'}: {str(e)}"
                    error_messages.append(error_msg)
                    _logger.error(error_msg)
            
            self.imported_invoices = imported_count
            self.skipped_invoices = skipped_count
            self.error_messages = '\n'.join(error_messages)
            
            # Hiển thị thông báo kết quả
            message = f"Import hoàn tất!\n"
            message += f"- Tổng số hóa đơn: {self.total_invoices}\n"
            message += f"- Đã import: {self.imported_invoices}\n"
            message += f"- Bỏ qua: {self.skipped_invoices}"
            
            if error_messages:
                message += f"\n\nLỗi:\n{self.error_messages}"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import XML'),
                    'message': message,
                    'type': 'success' if imported_count > 0 else 'warning',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            raise UserError(_('Lỗi khi đọc file XML: %s') % str(e))

    def _import_single_invoice(self, invoice_element):
        """Import một hóa đơn từ XML element"""
        # Tìm các phần tử chính
        ttchung = invoice_element.find('TTChung')
        nban = invoice_element.find('NDHDon/NBan')
        nmua = invoice_element.find('NDHDon/NMua')
        ttoan = invoice_element.find('NDHDon/TToan')
        hhdvus = invoice_element.findall('.//HHDVu')
        
        if not ttchung:
            raise ValidationError(_('Không tìm thấy thông tin chung hóa đơn'))
        
        # Tạo dữ liệu hóa đơn
        invoice_data = {
            'so_hoa_don': self._get_text(ttchung, 'SHDon'),
            'ky_hieu': self._get_text(ttchung, 'KHHDon'),
            'ngay_lap': self._parse_date(self._get_text(ttchung, 'NLap')),
            'nban_ten': self._get_text(nban, 'Ten') if nban else '',
            'nban_mst': self._get_text(nban, 'MST') if nban else '',
            'nban_dia_chi': self._get_text(nban, 'DChi') if nban else '',
            'nmua_ten': self._get_text(nmua, 'Ten') if nmua else '',
            'nmua_mst': self._get_text(nmua, 'MST') if nmua else '',
            'nmua_dia_chi': self._get_text(nmua, 'DChi') if nmua else '',
            'tong_tien': self._parse_float(self._get_text(ttoan, 'TgTTTBSo')) if ttoan else 0.0,
        }
        
        # Kiểm tra hóa đơn đã tồn tại
        existing = self.env['invoice.data.misa'].search([
            ('so_hoa_don', '=', invoice_data['so_hoa_don']),
            ('ky_hieu', '=', invoice_data['ky_hieu'])
        ])
        
        if existing:
            raise ValidationError(_('Hóa đơn đã tồn tại trong hệ thống'))
        
        # Tạo hóa đơn
        invoice = self.env['invoice.data.misa'].create(invoice_data)
        
        # Tạo các dòng hàng hóa dịch vụ
        for i, hhdvu in enumerate(hhdvus):
            line_data = {
                'invoice_id': invoice.id,
                'sequence': (i + 1) * 10,
                'ten': self._get_text(hhdvu, 'THHDVu'),
                'dvt': self._get_text(hhdvu, 'DVTinh'),
                'so_luong': self._parse_float(self._get_text(hhdvu, 'SLuong')),
                'don_gia': self._parse_float(self._get_text(hhdvu, 'DGia')),
                'thanh_tien': self._parse_float(self._get_text(hhdvu, 'ThTien')),
                'thue_suat': self._get_text(hhdvu, 'TSuat') or '0%',
            }
            self.env['invoice.data.misa.line'].create(line_data)
        
        return invoice

    def _get_text(self, element, tag_name):
        """Lấy text từ element con"""
        if element is None:
            return ''
        child = element.find(tag_name)
        return child.text if child is not None else ''

    def _parse_date(self, date_str):
        """Parse chuỗi ngày thành date object"""
        if not date_str:
            return False
        try:
            # Thử các format ngày khác nhau
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def _parse_float(self, value_str):
        """Parse chuỗi thành float"""
        if not value_str:
            return 0.0
        try:
            return float(value_str.replace(',', ''))
        except (ValueError, TypeError):
            return 0.0
