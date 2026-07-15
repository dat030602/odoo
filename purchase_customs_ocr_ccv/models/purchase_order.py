from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import logging
import os
import re
from datetime import datetime

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ocr_result_json = fields.Json(
        string='OCR Result (Debug)',
        readonly=True,
        copy=False,
        help='Raw OCR result'
    )

    def action_run_ocr(self):
        """Process attached documents to extract shipping information."""
        self.ensure_one()

        valid_mimetypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ]
        
        valid_attachments = self.customs_attachment_ids.filtered(
            lambda att: att.mimetype in valid_mimetypes and att.datas
        )
        
        if not valid_attachments:
            raise UserError("Please upload PDF, XLSX, or XLS files (EDO/BL/Manifest).")

        try:
            ocr_service = self.env['ocr.service'].sudo()
            file_data_list = []
            
            for att in valid_attachments:
                if att.datas:
                    if att.mimetype == 'application/pdf':
                        ext = 'pdf'
                    elif att.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                        ext = 'xlsx'
                    else:  # application/vnd.ms-excel
                        ext = 'xls'
                    
                    filename = att.name or f'document.{ext}'
                    if not filename.lower().endswith(f'.{ext}'):
                        filename = f"{os.path.splitext(filename)[0]}.{ext}"
                    
                    file_data_list.append({
                        'content': att.datas,
                        'name': filename,
                        'mimetype': att.mimetype
                    })

            if not file_data_list:
                raise UserError("No valid file data found in attachments.")

            ocr_result = ocr_service.process_file_with_gemini(file_data_list)
            self.ocr_result_json = json.dumps(ocr_result)
            action = self._process_ocr_results(ocr_result)
            
            return action

        except Exception as e:
            _logger.error("OCR processing failed for PO %s: %s", self.name, e, exc_info=True)
            raise UserError(f"OCR processing failed: {str(e)}")


    def _process_ocr_results(self, ocr_result):
        """Process and validate the OCR results"""
        self.ensure_one()

        if 'error' in ocr_result:
            raise UserError(ocr_result['error'])
        
        # Prepare write values
        write_vals = {}
        
        # Process main fields if they exist
        main_fields = [
            'carrier_name', 'bl_number', 'vessel_name',
            'voyage_number', 'arrival_date_estimated', 'custom_declaration_number', 'custom_declaration_date'
        ]
        
        # Add main fields to write values
        for field in main_fields:
            if field in ocr_result and ocr_result[field]:
                write_vals[field] = ocr_result[field]
        
        # Process container lines using x2many commands
        container_lines_commands = []
        po_line = self.order_line.filtered(lambda x: x.product_id)[:1]
        if 'stock_input_ids' in ocr_result and isinstance(ocr_result['stock_input_ids'], list):
            for item in ocr_result['stock_input_ids']:
                if not all(k in item for k in ['container_number', 'seal_number']):
                    continue

                command = None  
                existed = self.stock_input_ids.filtered(lambda x: x.container_number == item['container_number'])
                if existed:
                    command = (1, existed.id, {'seal_number': item['seal_number'].strip()})
                else:
                    command = (0, 0, {
                        'container_number': item['container_number'].strip(),
                        'seal_number': item['seal_number'].strip(),
                        'product_id': po_line.product_id.id,
                        'product_uom_id': po_line.product_uom.id,
                    })
                container_lines_commands.append(command)
        
        # Add container lines to write values
        if container_lines_commands:
            write_vals['stock_input_ids'] = container_lines_commands
        processed_count = len(container_lines_commands)
        
        # Perform a single write operation for all fields
        if write_vals:
            self.write(write_vals)
        
        # Update the raw OCR result for reference
        self.ocr_result_json = json.dumps(ocr_result, indent=2)


    def action_export_ocr_data(self):
        """Export OCR data to Excel for debugging/verification"""
        if not self.stock_input_ids:
            raise UserError("No OCR data to export. Please run OCR first.")
        
        # This can be extended to create Excel export
        return {
            'type': 'ir.actions.act_window',
            'name': 'OCR Data Export',
            'res_model': 'purchase.order.stock.input',
            'view_mode': 'tree',
            'domain': [('order_id', '=', self.id)],
            'target': 'new',
        }