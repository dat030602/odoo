from odoo import fields, models, api
from psycopg2 import DatabaseError
from odoo.tools import mute_logger


class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    # @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    # def _constrains_date_sequence(self):
    #     # Make it possible to bypass the constraint to allow edition of already messed up documents.
    #     # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
    #     constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
    #         'sequence.mixin.constraint_start_date',
    #         '1970-01-01'
    #     ))
    #     for record in self:
    #         if not record._must_check_constrains_date_sequence():
    #             continue


    # def _set_next_sequence(self):
    #     self.ensure_one()
    #     last_sequence = self._get_last_sequence()
    #     new = not last_sequence
    #     if new:
    #         last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

    #     format_string, format_values = self._get_sequence_format_param(last_sequence)
    #     if new:
    #         format_values['seq'] = 0
    #         format_values['year'] = self[self._sequence_date_field].year % (10 ** format_values['year_length'])
    #         format_values['month'] = self[self._sequence_date_field].month
    #     self.flush_recordset()
    #     registry = self.env.registry
    #     triggers = registry._field_triggers[self._fields[self._sequence_field]]
    #     for inverse_field, triggered_fields in triggers.items():
    #         for triggered_field in triggered_fields:
    #             if not triggered_field.store or not triggered_field.compute:
    #                 continue
    #             for field in registry.field_inverses[inverse_field[0]] if inverse_field else [None]:
    #                 self.env.add_to_compute(triggered_field, self[field.name] if field else self)
    #     while True:
    #         sequence_check = format_string.format(**format_values)
    #         value = sequence_check.split("/")[-1]
    #         sequence_new = sequence_check.replace(value, '')
    #         account_move = self.env['account.move'].search([('name', 'ilike', sequence_new)])
    #         number = []
    #         for seq in account_move:
    #             num = (seq.name).split("/")[-1]
    #             number_remove_0 = num.lstrip('0')
    #             number.append(int(number_remove_0))
    #         max_number = max(number) if number else 0
    #         format_values['seq'] = max_number + 1
    #         sequence = format_string.format(**format_values)
    #         try:
    #             with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
    #                 self[self._sequence_field] = sequence
    #                 self.flush_recordset([self._sequence_field])
    #                 break
    #         except DatabaseError as e:
    #             if e.pgcode not in ('23P01', '23505'):
    #                 raise e
    #     self._compute_split_sequence()
    #     self.flush_recordset(['sequence_prefix', 'sequence_number'])
