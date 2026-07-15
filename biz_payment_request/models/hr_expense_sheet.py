# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrExpenseSheet(models.Model):
	_inherit = "hr.expense.sheet"
 
	payment_request_id = fields.Many2one('payment.request', string="Đề nghị thanh toán")

	def action_sheet_move_create(self):
		res = super(HrExpenseSheet, self).action_sheet_move_create()
		for sheet in self:
			if sheet.payment_mode == 'company_account' and sheet.account_move_id:
				partner_id = sheet.employee_id.address_home_id or sheet.employee_id.user_partner_id
				
				parts = []
				if getattr(sheet, 'payment_request_id', False):
					parts.append(sheet.payment_request_id.name)
				
				internal_account_str = ""
				if getattr(sheet, 'internal_account_id', False):
					internal_account_str = sheet.internal_account_id.name
				elif getattr(sheet, 'internal_account_ids', False):
					internal_account_str = ", ".join(sheet.internal_account_ids.mapped('name'))
				
				if internal_account_str:
					parts.append(internal_account_str)
					
				if sheet.name:
					parts.append(sheet.name)
					
				new_ref = " - ".join(parts) if parts else (sheet.name or '')
				payment = sheet.account_move_id.payment_id
				
				payment_req_id = getattr(sheet, 'payment_request_id', False) and sheet.payment_request_id.id or None
				internal_acc_id = getattr(sheet, 'internal_account_id', False) and sheet.internal_account_id.id or None
				if not internal_acc_id and getattr(sheet, 'internal_account_ids', False):
					internal_acc_id = sheet.internal_account_ids[0].id
				
				# Update Partner and Ref directly using SQL to bypass standard validation
				if partner_id:
					if payment:
						self.env.cr.execute("""
							UPDATE account_payment 
							SET partner_id = %s, partner_type = 'supplier', ref = %s, note = %s
							WHERE id = %s
						""", (partner_id.id, new_ref, new_ref, payment.id))
						
					self.env.cr.execute("""
						UPDATE account_move 
						SET partner_id = %s, ref = %s, payment_request_id = %s, internal_account_id = %s, narration = %s, note = %s
						WHERE id = %s
					""", (partner_id.id, new_ref, payment_req_id, internal_acc_id, new_ref, new_ref, sheet.account_move_id.id))
					
					for line in sheet.account_move_id.line_ids:
						line_parts = parts.copy()
						if line.name and line.name != sheet.name:
							line_parts.append(line.name)
						new_name = " - ".join(line_parts) if line_parts else (line.name or '')
						self.env.cr.execute("""
							UPDATE account_move_line 
							SET partner_id = %s, name = %s 
							WHERE id = %s
						""", (partner_id.id, new_name, line.id))
				else:
					if payment:
						self.env.cr.execute("""
							UPDATE account_payment 
							SET ref = %s, note = %s
							WHERE id = %s
						""", (new_ref, new_ref, payment.id))

					# If no partner, just update ref
					self.env.cr.execute("""
						UPDATE account_move 
						SET ref = %s, payment_request_id = %s, internal_account_id = %s, narration = %s, note = %s
						WHERE id = %s
					""", (new_ref, payment_req_id, internal_acc_id, new_ref, new_ref, sheet.account_move_id.id))
					for line in sheet.account_move_id.line_ids:
						line_parts = parts.copy()
						if line.name and line.name != sheet.name:
							line_parts.append(line.name)
						new_name = " - ".join(line_parts) if line_parts else (line.name or '')
						self.env.cr.execute("""
							UPDATE account_move_line 
							SET name = %s 
							WHERE id = %s
						""", (new_name, line.id))
				
				# Use ORM to ensure related fields on UI (like narration, payment_reference) are fully populated and cached
				try:
					update_vals = {
						'narration': new_ref,
						'note': new_ref,
						'payment_reference': new_ref
					}
					sheet.account_move_id.with_context(check_move_validity=False).write(update_vals)
					if payment:
						payment.with_context(check_move_validity=False).write(update_vals)
				except Exception:
					pass
		return res