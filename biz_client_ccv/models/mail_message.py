# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from functools import lru_cache


class MailMessage(models.Model):
	_inherit = 'mail.message'

	def delete_record_not_exists(self):

		query = """
		select model
		from mail_message  
		where model is not null and res_id is not null

		group by model

		"""

		self.env.cr.execute(query)
		result = self.env.cr.fetchall()
		for res in result:
			try:
				model = res[0]
				table = model.replace('.','_')
				query2 = """
				with a as (select m.id
					from mail_message m
					left join {table} a on a.id = m.res_id
					where m.model = '{model}' and m.res_id is not null and a.id is null
					)
					delete from mail_message where id in (select * from a)
				""".format(model=model, table=table)
				self.env.cr.execute(query2)
				self.env.cr.commit()

			except:
				pass