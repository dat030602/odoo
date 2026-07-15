# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

DAY_OF_WEEK = [
	('Monday', '0'),
	('Tuesday', '1'),
	('Wednesday', '2'),
	('Thursday', '3'),
	('Friday', '4'),
	('Saturday', '5'),
	('Sunday', '6')
]

def get_number_specified_weekdays(start_date, end_date, weekday_list=[]):
	"""
	Count number of weekdays in a date range.

	Args:
		start_date (date): start date of the date range
		end_date (date): end date of the date range
		weekday_list (list): list of weekday name in str (e.g. ['Monday', 'Tuesday']). Default is empty list means count all weekdays.

	Returns:
		int: number of weekdays in the date range
	"""
	if not start_date or not end_date:
		return 0
		
	count = 0
	current_date = start_date
	while current_date <= end_date:
		DAY_OF_WEEK_dict = dict(DAY_OF_WEEK)
		
		if DAY_OF_WEEK_dict.get(current_date.strftime('%A')) in weekday_list:
			count += 1
		current_date += timedelta(days=1)

	return count

def convert_float_to_time(time):
	return '{0:02.0f}:{1:02.0f}'.format(*divmod(float(time) * 60, 60))

count_character = {'X': 1,'X/2': 0.5,'2X/8': 0.25,'1X/8': 0.125,'6X/8': 0.75,'7X/8': 0.875,'15X/16': 0.9375,'13X/16': 0.8125,'3X/16': 0.1875,'7X/16': 0.4375,'3X/8': 0.375,'5X/8': 0.625,'PN': 1,'PN/2': 0.5,'2PN/8': 0.25,'1PN/8': 0.125,'6PN/8': 0.75,'7PN/8': 0.875,'15PN/16': 0.9375,'13PN/16': 0.8125,'3PN/16': 0.1875,'7PN/16': 0.4375,'3PN/8': 0.375,'5PN/8': 0.625}

count_character_PN = {'PN': 1,'PN/2': 0.5,'2PN/8': 0.25,'1PN/8': 0.125,'6PN/8': 0.75,'7PN/8': 0.875,'15PN/16': 0.9375,'13PN/16': 0.8125,'3PN/16': 0.1875,'7PN/16': 0.4375,'3PN/8': 0.375,'5PN/8': 0.625}

def count_date(self,character):
	count = 0
	for i in range(1,32):
		date_field = self['date_%s'%i]
		if date_field and date_field in character:
			if count_character.get(date_field):
				count += count_character.get(date_field)
				continue
			count += 1
	return count

def count_date_pn(self,character):
	count = 0
	for i in range(1,32):
		date_field = self['date_%s'%i]
		if date_field and date_field in character:
			if count_character_PN.get(date_field):
				count += 1 - count_character_PN.get(date_field)
				continue
			count += 1
	return count

def count_date_tc(self):
	total_hours = 0.0
	for i in range(1,32):
		date_field = self['date_%s'%i]
		if date_field:
			try:
				parts = date_field.split(':')
				hours, minutes, seconds = map(int, parts)
				# Convert the time to total hours
				time_hours = timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds() / 3600
				total_hours += time_hours
			except Exception as e:
				pass
	return total_hours

# mã: ['trường để tính amount','tên']
code_table = {
	'NC': ['nc_hc','Ngày công'],
	'NCC': [False,'Ngày công chuẩn'],
	'TC': ['time_tc','Tăng ca'],
	'NCLP': ['nn_pn','NCLP'],
	'NCLL': ['nc_l','NCLL'],
	'NCPKL': ['nn_p','Nghỉ phép không lương'],
}

class SummaryFromTimekeepingMachine(models.Model):
	_name = 'summary.from.timekeeping.machine'
	_description = 'Summary From Timekeeping Machine'

	month = fields.Selection([
		('01','Month 1'),('02','Month 2'),('03','Month 3'),
		('04','Month 4'),('05','Month 5'),('06','Month 6'),
		('07','Month 7'),('08','Month 8'),('09','Month 9'),
		('10','Month 10'),('11','Month 11'),('12','Month 12')],
		string='Month',required=True)

	year = fields.Selection([
		('2023','2023'),('2024','2024'),('2025','2025'),
		('2026','2026'),('2027','2027'),('2028','2028'),
		('2029','2029'),('2030','2030'),('2031','2031'),
		('2032','2032'),('2033','2033'),('2034','2035')],
		string='Year',required=True)

	worksheet_name = fields.Char('Worksheet name')
	
	def name_get(self):
		result = []
		for inv in self:
			result.append((inv.id, "%s/%s" % (inv.month,inv.year)))
		return result

	employee_ids = fields.Many2many('hr.employee',string='Employees')

	summary_common_ids = fields.One2many('summary.common','summary_id','Summary Common')
	summary_overtime_ids = fields.One2many('summary.overtime','summary_id','Summary Overtime')

	standard_working_days = fields.Float('Standard Working Days')

	def action_work_sumary(self):
		self.summary_common_ids.filtered(lambda x: x.check_create_from_button).unlink()
		self.summary_overtime_ids.filtered(lambda x: x.check_create_from_button).unlink()

		Employee = self.env['hr.employee'].sudo()
		Attendance = self.env['hr.attendance'].sudo()
		employee_ids = self.employee_ids if self.employee_ids else Employee.search([])
		summary_common = []
		summary_overtime = []

		def get_date(employee,table):
			stt = 0
			domain = [('employee_id','=',employee.id)]
			v = {'employee_id': empl.id,'position': empl.job_id and empl.job_id.name or False,'check_create_from_button': True}

			def get_hour_finish(employee,date_check):
				get_calendar = employee.resource_calendar_id.attendance_ids.filtered(lambda x: x.dayofweek == str(date_check.weekday()) and x.day_period)
				finish = False
				if get_calendar:
					finish = get_calendar.filtered(lambda x: x.day_period == 'afternoon')
					if finish:
						finish = finish.hour_to or False
					else:
						finish = get_calendar[0].hour_to or False
				return finish

			for i in range(1,32):
				check_result = False
				#check xem ngày đó có phù hợp với tháng đó kh.. nếu kh có thì kh cần tìm mà bỏ qua
				try:
					date_0_hour = datetime.strptime('%s/%s/%s 00:00:00'%(str(i),self.month,self.year), '%d/%m/%Y %H:%M:%S') - timedelta(hours=7)
					date_24_hour = datetime.strptime('%s/%s/%s 23:59:59'%(str(i),self.month,self.year), '%d/%m/%Y %H:%M:%S') - timedelta(hours=7)
				except:
					continue
				if table == 'summary_common':
					
					check_x = Attendance.search(domain + [('check_in','>=',date_0_hour),('check_in','<=',date_24_hour)],limit=1)
					if check_x:
						# Bổ sung kiểm tra nghỉ phép
						leave_obj = self.env['hr.leave']
						leave_domain = [
							('employee_id', '=', employee.id),
							('state', '=', 'validate'),
							('date_from', '<=', date_24_hour),
							('date_to', '>=', date_0_hour),
						]
						leave = leave_obj.search(leave_domain, limit=1)
						if leave:
							leave_type = leave.holiday_status_id.work_entry_type_id.code
							if leave_type == 'LEAVE120':
								if leave.request_unit_half:
									check_result = 'PN/2';
								else:
									# Tính số giờ nghỉ phép
									leave_from = leave.date_from + timedelta(hours=7)
									leave_to = leave.date_to + timedelta(hours=7)
									# Giới hạn trong ngày đang xét
									leave_from = max(leave_from, date_0_hour)
									leave_to = min(leave_to, date_24_hour)
									# Tính số giờ nghỉ
									leave_hours = (leave_to - leave_from).total_seconds() / 3600.0
									# Xử lý nghỉ trưa
									noon_start = leave_from.replace(hour=12, minute=0, second=0, microsecond=0)
									noon_end = leave_from.replace(hour=13, minute=0, second=0, microsecond=0)
									# Nếu nghỉ xuyên trưa
									if leave_from <= noon_start and leave_to >= noon_end:
										leave_hours -= 1
									# Nếu nghỉ kết thúc trong khoảng trưa
									elif noon_start <= leave_to <= noon_end:
										leave_hours -= (leave_to - noon_start).total_seconds() / 3600.0
									# Nếu nghỉ bắt đầu trong khoảng trưa
									elif noon_start <= leave_from <= noon_end:
										leave_hours -= (noon_end - leave_from).total_seconds() / 3600.0
									# Tính kết quả
									leave_value = round(8 - leave_hours, 2)
									X = 8
									if leave_value != int(leave_value):
										leave_value = leave_value * 2
										X = 8 * 2
									check_result = str(int(round(leave_value, 2))) + 'PN' + '/' + str(X)
							elif leave_type == 'LEAVE100':
								# Tính số giờ nghỉ phép
								leave_from = leave.date_from + timedelta(hours=7)
								leave_to = leave.date_to + timedelta(hours=7)
								# Giới hạn trong ngày đang xét
								leave_from = max(leave_from, date_0_hour)
								leave_to = min(leave_to, date_24_hour)
								# Tính số giờ nghỉ
								leave_hours = (leave_to - leave_from).total_seconds() / 3600.0
								# Xử lý nghỉ trưa
								noon_start = leave_from.replace(hour=12, minute=0, second=0, microsecond=0)
								noon_end = leave_from.replace(hour=13, minute=0, second=0, microsecond=0)
								# Nếu nghỉ xuyên trưa
								if leave_from <= noon_start and leave_to >= noon_end:
									leave_hours -= 1
								# Nếu nghỉ kết thúc trong khoảng trưa
								elif noon_start <= leave_to <= noon_end:
									leave_hours -= (leave_to - noon_start).total_seconds() / 3600.0
								# Nếu nghỉ bắt đầu trong khoảng trưa
								elif noon_start <= leave_from <= noon_end:
									leave_hours -= (noon_end - leave_from).total_seconds() / 3600.0
								# Tính kết quả
								leave_value = round(8 - leave_hours, 2)
								X = 8
								if leave_value != int(leave_value):
									leave_value = leave_value * 2
									X = 8 * 2
								check_result = str(int(round(leave_value, 2))) + 'X' + '/' + str(X)
								if leave.request_unit_half:
									check_result = 'X/2'
							else:
								check_result = 'X'
						else:
							check_result = 'X'

					hour_work = 0

					if not check_result:
						
						search_holiday = self.env['resource.calendar.leaves'].sudo().search([('resource_id','=',False)])
						date_se = date_0_hour + timedelta(hours=10)
						search_holiday = search_holiday.filtered(lambda x: x.date_from.date() <= date_se.date() and date_se.date() <= x.date_to.date())
						if not hour_work:
							if search_holiday:
								check_result = 'L'
						# Bổ sung kiểm tra nghỉ phép nếu không có check_result
						if not search_holiday:
							leave_obj = self.env['hr.leave']
							leave_domain = [
								('employee_id', '=', employee.id),
								('state', '=', 'validate'),
								('date_from', '<=', date_se),
								('date_to', '>=', date_se),
							]
							leave = leave_obj.search(leave_domain, limit=1)
							if leave:
								leave_type = leave.holiday_status_id.work_entry_type_id.code
								if leave_type == 'LEAVE120':
									check_result = 'PN'
								elif leave_type == 'LEAVE100':
									check_result = 'P'
							else:
								# Bổ sung: nếu không có leave, kiểm tra ngày đó có trong lịch làm việc không
								calendar = employee.resource_calendar_id
								if calendar:
									# Xác định thứ trong tuần
									weekday = str((date_se + timedelta(hours=10)).weekday())
									has_work = calendar.attendance_ids.filtered(lambda x: x.dayofweek == weekday)
									if has_work and employee.skip_timekeeping_machine:
										check_result = 'X'
									elif has_work and not check_x and not leave and not search_holiday:
										check_result = 'Ro'
									

				if table == 'summary_overtime':
					stt += 1
					filter_date = False
					#check có lấy đc hour_to để so sánh với thời gian checkout không
					hour_finish = get_hour_finish(employee,date_24_hour)
					if hour_finish:
						hour = convert_float_to_time(hour_finish).split(':')
						hour_to = datetime.strptime('%s/%s/%s %s:%s:00'%(str(i),self.month,self.year,hour[0],hour[1]), '%d/%m/%Y %H:%M:%S')
						#TH1: tìm dòng check_out = false và check_in > giờ kết thúc => ngày 1 = check_in - giờ kết thúc
						filter_date = Attendance.search(domain + [('check_out','=',False),('check_in','>',hour_to),('check_in','>=',date_0_hour),('check_in','<=',date_24_hour)],limit=1)
						#TH2: không tìm được dòng có check_out = false thì lấy dòng có check_out lớn nhất và check_out > giờ kết thúc => ngày 1 = check_out - giờ kết thúc
						if not filter_date:
							filter_date = Attendance.search(domain + [('check_out','>=',date_0_hour),('check_out','<=',date_24_hour)],limit=1,order="check_out asc")

						if employee.resource_calendar_id and employee.resource_calendar_id.attendance_ids and filter_date:
							date_compare = (filter_date.check_out and filter_date.check_out + timedelta(hours=7) or False)\
							 or (filter_date.check_in and filter_date.check_in + timedelta(hours=7) or False)
							if date_compare and date_compare > hour_to:
								check_result = str(date_compare - hour_to)

				v.update({'date_%s'%i: check_result if check_result else False})
			return v

		for empl in employee_ids:
			#bảng tổng hợp chung
			summary_common.append(get_date(empl,"summary_common"))
			#bảng tăng ca(nếu check tự động tính tăng ca mới tính)
			if empl.automatically_calculate_overtime:
				summary_overtime.append(get_date(empl,"summary_overtime"))

		self.summary_common_ids = [(0,0,sumary) for sumary in summary_common]
		self.summary_overtime_ids = [(0,0,sumary) for sumary in summary_overtime]	


	def salary_calculation(self):
		summary_common_employees = self.summary_common_ids.mapped('employee_id')
		self.create_allowance_month(summary_common_employees,['NC','NCC','NCLP','NCLL','NCPKL'],'summary_common_ids')
		#TC
		summary_overtime_employees = self.summary_overtime_ids.mapped('employee_id')
		self.create_allowance_month(summary_overtime_employees,['TC'],'summary_overtime_ids')

	def create_allowance_month(self,employees,codes,field_table):
		HrContract = self.env['hr.contract'].sudo()
		HrAllowance = self.env['hr.allowance'].sudo()
		year = int(self.year)
		month = str(int(self.month))
		for empl in employees:
			contracts = HrContract.search([('employee_id','=',empl.id),('state','=','open')])
			#xóa dòng trong bảng phụ cấp tháng trước
			for contract in contracts:
				allowance_month = contract.allowance_month_ids.filtered(lambda x: x.year == year and x.month == month and x.code in codes)
				if allowance_month:
					allowance_month.unlink()
			
			#tạo lại sau khi xóa
			for line in self[field_table].filtered(lambda x: x.employee_id == empl):
				for code in codes:
					for contract in contracts:
						amount = line[code_table.get(code)[0]] or 0 
						name = code_table.get(code)[1] or ''
						if code == 'NCC' and field_table == 'summary_common_ids':
							amount = line.standard_working_days

						allowance_id = HrAllowance.search([('name','=', name),('code','=',code)])
						if not allowance_id:
							allowance_id = HrAllowance.create({'name': name,'code': code,'is_fixed': True})
						v = {'amount': amount, 'allowance_id': allowance_id.id, 'year': year, 'month': month, 'code': code}
						contract.allowance_month_ids = [(0,0,v)]

class SummaryCommon(models.Model):
	_name = 'summary.common'
	_description = 'Summary Common'

	summary_id = fields.Many2one('summary.from.timekeeping.machine')
	employee_id = fields.Many2one('hr.employee','Employee')
	position = fields.Char('Position')
	date_1 = fields.Char('Date 1')
	date_2 = fields.Char('Date 2')
	date_3 = fields.Char('Date 3')
	date_4 = fields.Char('Date 4')
	date_5 = fields.Char('Date 5')
	date_6 = fields.Char('Date 6')
	date_7 = fields.Char('Date 7')
	date_8 = fields.Char('Date 8')
	date_9 = fields.Char('Date 9')
	date_10 = fields.Char('Date 10')
	date_11 = fields.Char('Date 11')
	date_12 = fields.Char('Date 12')
	date_13 = fields.Char('Date 13')
	date_14 = fields.Char('Date 14')
	date_15 = fields.Char('Date 15')
	date_16 = fields.Char('Date 16')
	date_17 = fields.Char('Date 17')
	date_18 = fields.Char('Date 18')
	date_19 = fields.Char('Date 19')
	date_20 = fields.Char('Date 20')
	date_21 = fields.Char('Date 21')
	date_22 = fields.Char('Date 22')
	date_23 = fields.Char('Date 23')
	date_24 = fields.Char('Date 24')
	date_25 = fields.Char('Date 25')
	date_26 = fields.Char('Date 26')
	date_27 = fields.Char('Date 27')
	date_28 = fields.Char('Date 28')
	date_29 = fields.Char('Date 29')
	date_30 = fields.Char('Date 30')
	date_31 = fields.Char('Date 31')
	nc_hc = fields.Float('NC HC',compute="_compute_nc_hc")
	nc_l = fields.Float('NC L',compute="_compute_nc_l")
	nn_p = fields.Float('NN P',compute="_compute_nn_p")
	nn_k = fields.Float('NN K',compute="_compute_nn_k")
	nn_pn = fields.Float('NN PN',compute="_compute_nn_pn")
	note = fields.Text('Note')
	check_create_from_button = fields.Boolean()

	standard_working_days = fields.Float(compute='_compute_standard_working_days', string='Standard working days',store=True)

	@api.depends(
			'summary_id.month',
			'summary_id.year',
			'employee_id',
			'employee_id.resource_calendar_id',
			'summary_id.standard_working_days',
	)
	def _compute_standard_working_days(self):
		for res in self:
			if res.summary_id.standard_working_days:
				res.standard_working_days = res.summary_id.standard_working_days
				continue

			standard_working_days = 0
			if res.summary_id.month and res.summary_id.year:
				date_from = datetime.strptime('%s/%s'%(str(res.summary_id.month),str(res.summary_id.year)),'%m/%Y')
				date_to = date_from + relativedelta(months=1) - timedelta(seconds=1)
				if res.employee_id and res.employee_id.resource_calendar_id:
					days_list = set()
					for attendance in res.employee_id.resource_calendar_id.attendance_ids:
						days_list.add(attendance.dayofweek)
					
					standard_working_days = get_number_specified_weekdays(date_from, date_to, days_list)

			res.standard_working_days = standard_working_days

	def _compute_nc_hc(self):
		for res in self:
			res.nc_hc = count_date(res,['X','X/2','2X/8','1X/8','6X/8','7X/8','15X/16','13X/16','3X/16','7X/16','3X/8','5X/8','PN/2','PN','2PN/8','1PN/8','6PN/8','7PN/8','15PN/16','13PN/16','3PN/16','7PN/16','3PN/8','5PN/8']) if not res.employee_id.default_enough_work else res.standard_working_days

	def _compute_nc_l(self):
		for res in self:
			res.nc_l = count_date(res,['L'])

	def _compute_nn_p(self):
		for res in self:
			res.nn_p = count_date(res,['P'])

	def _compute_nn_k(self):
		for res in self:
			res.nn_k = count_date(res,['Ro','X/2'])

	def _compute_nn_pn(self):
		for res in self:
			res.nn_pn = count_date(res,['PN']) + count_date_pn(res,['PN/2','2PN/8','1PN/8','6PN/8','7PN/8','15PN/16','13PN/16','3PN/16','7PN/16','3PN/8','5PN/8'])

class SummaryOvertime(models.Model):
	_name = 'summary.overtime'
	_description = 'Summary Overtime'

	summary_id = fields.Many2one('summary.from.timekeeping.machine')
	employee_id = fields.Many2one('hr.employee','Employee')
	position = fields.Char('Position')
	date_1 = fields.Char('Date 1')
	date_2 = fields.Char('Date 2')
	date_3 = fields.Char('Date 3')
	date_4 = fields.Char('Date 4')
	date_5 = fields.Char('Date 5')
	date_6 = fields.Char('Date 6')
	date_7 = fields.Char('Date 7')
	date_8 = fields.Char('Date 8')
	date_9 = fields.Char('Date 9')
	date_10 = fields.Char('Date 10')
	date_11 = fields.Char('Date 11')
	date_12 = fields.Char('Date 12')
	date_13 = fields.Char('Date 13')
	date_14 = fields.Char('Date 14')
	date_15 = fields.Char('Date 15')
	date_16 = fields.Char('Date 16')
	date_17 = fields.Char('Date 17')
	date_18 = fields.Char('Date 18')
	date_19 = fields.Char('Date 19')
	date_20 = fields.Char('Date 20')
	date_21 = fields.Char('Date 21')
	date_22 = fields.Char('Date 22')
	date_23 = fields.Char('Date 23')
	date_24 = fields.Char('Date 24')
	date_25 = fields.Char('Date 25')
	date_26 = fields.Char('Date 26')
	date_27 = fields.Char('Date 27')
	date_28 = fields.Char('Date 28')
	date_29 = fields.Char('Date 29')
	date_30 = fields.Char('Date 30')
	date_31 = fields.Char('Date 31')
	time_tc = fields.Float('Time TC',compute="_compute_time_tc")
	note = fields.Text('Note')
	check_create_from_button = fields.Boolean()

	def _compute_time_tc(self):
		for res in self:
			res.time_tc = count_date_tc(res)

	@api.model_create_multi
	def create(self,vals):
		res = super(SummaryOvertime,self).create(vals)
		for rec in res:
			rec.check_input_date()
		return res

	def write(self,vals):
		res = super(SummaryOvertime,self).write(vals)
		for rec in self:
			rec.check_input_date()
		return res

	def check_input_date(self):
		for i in range(1,32):
			date_field = self['date_%s'%i]
			if date_field:
				try:
					parts = date_field.split(':')
					if len(parts) != 3:
						raise ValidationError('Vui lòng nhập đúng định dạng HH:MM:SS')
					hours, minutes, seconds = map(int, parts)
					# Convert the time to total hours
					time_hours = timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds() / 3600
				except Exception as e:
					raise ValidationError(e)