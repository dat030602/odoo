# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,  _
import json
from odoo.exceptions import UserError, ValidationError
import datetime
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
	_inherit = 'stock.picking'

	conveyor_log_ids = fields.One2many("conveyor.log",'picking_id', 'Conveyor log')
	vehicle_license_plate = fields.Char("Vehicle license plate", copy=False, tracking=True)
	vehicle_driver_name = fields.Char("Tài xế", copy=False)
	conveyor_start = fields.Integer("Conveyor start number")
	conveyor_end = fields.Integer("Conveyor end number")
	conveyor_realnum = fields.Float("Conveyor real number", compute="compute_real_number", store=True)
	conveyor_lineid = fields.Selection([
			('7', 'Băng tải của 15'),
			('2', 'Băng tải của 7'),
			('3', 'Băng tải của 9'),
			('4', 'Băng tải của 11'),
			('1', 'Băng tải của 4'),
			('8', 'Băng tải của 14'),
			('6', 'Băng tải của 6'),
			('5', 'Băng tải của 16')
		], string="LineID")

	check_conveyor_data = fields.Boolean("Check conveyor data")

	@api.onchange('vehicle_license_plate')
	def _onchange_vehicle_license_plate(self):
		if self.vehicle_license_plate:
			import re
			# Bỏ hết các ký tự đặc biệt, chỉ lấy số và chữ
			plate = self.vehicle_license_plate.replace(" ", "").replace(".", "").replace(",", "").replace("_", "").replace("-", "")
			matches = []
			# Tìm pattern: 2 số, 1 chữ, 4-5 số (cho phép 4 hoặc 5 số cuối)
			pattern = re.compile(r'(\d{2})([A-Z])(\d{5})', re.IGNORECASE)
			result = pattern.search(plate)
			if result:
				num1, char, num2 = result.groups()
				if len(num2) == 4:
					num2 = "0" + num2
				# Không thêm dấu gạch nối
				formatted_plate = f"{num1}{char.upper()}{num2}"
				matches = [formatted_plate]
			if matches:
				self.vehicle_license_plate = matches[0].strip()
			
			in_out_line = self.env['sale.vehicle.in.out.line'].search([('vehicle_num', '=', self.vehicle_license_plate)], limit=1)
			if in_out_line:
				self.vehicle_driver_name = in_out_line.vehicle_driver
				self.department_ids |= in_out_line.loading_id

	@api.depends('conveyor_log_ids')
	def compute_real_number(self):
		for pick in self:
			number = 0
			conveyor_log_ids = pick.conveyor_log_ids and pick.conveyor_log_ids.filtered(lambda x: x.state == 'done' and not x.is_push) or False 
			if conveyor_log_ids:
				first_con = conveyor_log_ids[0]
				try:
					res = json.loads(first_con.response)
					for data in res:
						if data.get("MO_RealNum", False):
							number += float(data['MO_RealNum'])
				except Exception as e:
					pass

			pick.conveyor_realnum = number

#	def button_validate(self):
#		picking = super(StockPicking, self).button_validate()
#		for res in self:
#			if res.picking_type_id.code == 'outgoing':
#				res.send_to_conveyor()
#		return picking

	def send_to_conveyor(self):
		Log = self.env['conveyor.log']

		if not self.conveyor_lineid:
			raise ValidationError(_("Please select LineID to push bagcouter"))

		if not self.vehicle_license_plate:
			raise ValidationError(_('Invalid params Vehicle license plate. Please check again!'))

		note = ""
		if self.stocker_id:
			note += "TK " + (self.stocker_id.name_without_position or self.stocker_id.name or "") + " "
		if self.department_ids:
			note += ", ".join(self.department_ids.mapped('name'))
		
		data = {
			'LineID': self.conveyor_lineid,
			"MO_Code": self.name,
			"MO_Custommer": self.partner_id.name,
			"MO_Tranz": self.vehicle_license_plate,
			'MO_ChieuDH': 1,
			'MO_Note': note,
			'Product':  []
		}
		for line in self.move_ids_without_package:
			if not line.product_id.default_code or not line.product_id.default_specification_id:
				raise ValidationError(_('Invalid params product code. Please check again!'))

			data['Product'].append({
				"ProCode": line.product_id.default_code,
				"ProName": line.product_id.name,
				"ProLen": line.product_id.default_specification_id.product_length if line.product_id.default_specification_id else 0,
				'StartNum': 0,
				'PlanNum': line.bag_number,
			})		
		params = {
			'Push_MO_Bagcounter': json.dumps(data),
		}
		_logger.info('$$$$$$$$$$$$$$$$$$$$ %s', data)
		res = Log.execute_api(self, data=params, is_push=True)

	def push_conveyor_data(self, data, is_realtime=False):
		ConveyorData = self.env['conveyor.data']
		# ConveyorProductData = self.env['conveyor.product.data']
		conveyor_data_id = False
		if data and not is_realtime and data[0].get('MO_Code_Odoo', False):
			conveyor_data_id = self.env['conveyor.data'].search([('mo_code_odoo', '=', data[0].get('MO_Code_Odoo', ''))], limit=1)
		elif data  and is_realtime and data[1].get('MO_Code', False):
			conveyor_data_id = self.env['conveyor.data'].search([('mo_code_odoo', '=', data[1].get('MO_Code', ''))], limit=1)
		else:
			return

		vals = {
			'mo_code_odoo': data[0].get('MO_Code_Odoo', '') or (data[1].get('MO_Code', '') if is_realtime else ''),
			'mo_customer': data[0].get('MO_Custommer', '') or (data[1].get('MO_Custommer', '') if is_realtime else ''),
			'mo_tranz': self.vehicle_license_plate or (data[1].get('MO_Tranz', '') if is_realtime else ''),
			'mo_start_time': data[0].get('MO_StartTime', '') or (data[1].get('MO_StartTime', '') if is_realtime else ''),
			'mo_close_time': data[0].get('MO_CloseTime', '') or (data[1].get('MO_CloseTime', '') if is_realtime else ''),
			'mo_note': data[0].get('MO_Note', '') or (data[1].get('MO_Note', '') if is_realtime else ''),
			'product_data_ids': [],
		}

		product_lines = []
		if not is_realtime:
			for prod in data[1].get('Product', []):
				print(prod)
				product_line = {
					'pro_code': prod.get('ProCode', ''),
					'pro_name': prod.get('ProName', ''),
					'mo_plan_num': float(prod.get('MO_PlanNum', 0)),
					'mo_real_num': float(prod.get('MO_RealNum', 0)),
					'mo_start_num': float(prod.get('MO_StartNum', 0)),
					'index_0': prod.get('0', ''),
					'index_1': prod.get('1', ''),
					'index_2': prod.get('2', ''),
					'index_3': prod.get('3', ''),
					'index_4': prod.get('4', ''),
				}
				product_lines.append((0, 0, product_line))
		vals['product_data_ids'] = product_lines
		if conveyor_data_id:
			conveyor_data_id.write(vals)
		else:
			ConveyorData.create(vals)

	def get_bagcouter_from_conveyor(self, name=False):
		Log = self.env['conveyor.log']

		# if not self.conveyor_lineid:
		# 	raise ValidationError(_("Please select LineID to push bagcouter"))
		
		if not name:
			name = self.name
		params = {
			'Get_MOOld_Bagcouter': json.dumps({'MOCode': name})
		}
		res = Log.execute_api(self, data=params)
		self.push_conveyor_data(res.get('data', False))
		return res
	
	def get_realtime_conveyor_data(self, line_id):
		Log = self.env['conveyor.log']
		params = {
			'Get_MOLive_Bagcouter': json.dumps({'LineID': line_id})
		}
		res = Log.execute_api(self, data=params)
		return res

	def _cron_get_realtime_conveyor_data(self, date=False):
		keys = [key[0] for key in self._fields['conveyor_lineid'].selection]
		for key in keys:
			res = self.get_realtime_conveyor_data(int(key))
			if res.get("error", False):
				return
			data = res['data']
			if data:
				self.push_conveyor_data(data, is_realtime=True)
		self.clear_conveyor_log()

	def _cron_fetch_conveyor(self, date=False):
		date_from = date or datetime.date.today()
		stock_picking = self.search([('vehicle_license_plate', '!=', False), ('conveyor_lineid', '!=', False), ('stock_date_receipt','>=', date_from)])
		if stock_picking:
			index = 1
			for pick in stock_picking:
				_logger.info('Đang lấy dữ liệu băng tải %s (%s/%s)', pick.name, index, len(stock_picking))
				index += 1
				res = pick.get_bagcouter_from_conveyor()
				if res.get("error", False):
					return

				data = res['data']
				if data:
					pick.write({'check_conveyor_data': True})
					for val in data:
						if val.get("MO_Code", False):
							picking = self.sudo().search([('name','=', val['MO_Code'])], limit=1)
							if picking:
								picking.write({'conveyor_log_ids': [(4, res['queue'])]})
		conveyor_ids = self.env['conveyor.data'].search([('create_date', '=', date_from)])
		if conveyor_ids:
			index = 1
			for conveyor_id in conveyor_ids:
				_logger.info('Đang lấy dữ liệu băng tải %s (%s/%s)', conveyor_id.mo_code_odoo, index, len(conveyor_ids))
				index += 1
				res = self.get_bagcouter_from_conveyor(conveyor_id.mo_code_odoo)
		self.clear_conveyor_log()

	def clear_conveyor_log(self):
		self.env['conveyor.log'].search(
			[('create_date','<=', datetime.datetime.now() - datetime.timedelta(days=7))],
			limit=100,
			order="create_date ASC"  # sửa dòng này
		).unlink()
		self.env['conveyor.log'].search(
			['|', ('response','=', False),('response','=', '')],
			limit=100,
			order="create_date ASC"  # sửa dòng này
		).unlink()


