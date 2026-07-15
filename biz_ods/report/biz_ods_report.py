# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api


class CallHistoryReport(models.Model):
    _name = "biz.ods.call.history.report"
    _auto = False
    _description = "ODS Call History Analysis"

    ods_key = fields.Char(string="Key", readonly=True)
    ods_call_date = fields.Datetime(string="Call Date", readonly=True)
    ods_call_only_date = fields.Date(string="Call Date(Only Date)", readonly=True)
    ods_head_number = fields.Char(string="Head Number", readonly=True)
    ods_receive_number = fields.Char(string="Receive Number", readonly=True)
    ods_receive_group = fields.Char(string="Receive Group", readonly=True)
    ods_status = fields.Selection(selection=[
        ('answered', "Answer"),
        ('no_answer', "No Answer"),
        ('busy', "Busy"),
        ('failed', "Failed"),
        ('cancel', "Cancel"),
        ('answered_elsewhere', 'Answered Elsewhere')
    ], string="Status", readonly=True)
    ods_link_file = fields.Char(string="Link File", readonly=True)
    ods_type_call = fields.Selection(selection=[
        ('inbound', "Inbound"),
        ('outbound', "Outbound"),
        ('local', "Local")
    ], string="Type Call", readonly=True)
    ods_total_call_time = fields.Integer(string="Total Call Time", readonly=True)
    ods_real_call_time = fields.Integer(string="Real Call Time", readonly=True)

    #
    caller_name = fields.Char(string="Caller Name", readonly=True)
    receive_name = fields.Char(string="Receive Name", readonly=True)
    call_content = fields.Text(string="Call Content", readonly=True)
    # Relational
    caller_partner_id = fields.Many2one(comodel_name="res.partner", string="Caller Partner ID", readonly=True)
    caller_user_id = fields.Many2one(comodel_name="res.users", string="Caller User ID", readonly=True)
    receive_partner_id = fields.Many2one(comodel_name="res.partner", string="Receive Partner ID", readonly=True)
    receive_user_id = fields.Many2one(comodel_name="res.users", string="Receive User ID", readonly=True)

    @property
    def _table_query(self):
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    def _select(self):
        return '''
            SELECT
                MIN(callHistory.id) AS id,
                callHistory.ods_key AS ods_key,
                callHistory.ods_call_date AS ods_call_date,
                callHistory.ods_call_only_date AS ods_call_only_date,
                callHistory.ods_caller_number AS ods_caller_number,
                callHistory.ods_head_number AS ods_head_number,
                callHistory.ods_receive_number AS ods_receive_number,
                callHistory.ods_receive_group AS ods_receive_group,
                callHistory.ods_status AS ods_status,
                callHistory.ods_link_file AS ods_link_file,
                callHistory.ods_type_call AS ods_type_call,
                callHistory.caller_name AS caller_name,
                callHistory.caller_name AS caller_name,
                callHistory.receive_name AS receive_name,
                callHistory.ods_total_call_time AS ods_total_call_time,
                callHistory.ods_real_call_time AS ods_real_call_time,
                callHistory.call_content AS call_content,
                callHistory.caller_partner_id AS caller_partner_id,
                callHistory.caller_user_id AS caller_user_id,
                callHistory.receive_partner_id AS receive_partner_id,
                callHistory.receive_user_id AS receive_user_id
        '''

    def _from(self):
        return '''
            FROM biz_ods_call_history callHistory
                LEFT JOIN res_users resUser ON (resUser.id = callHistory.caller_user_id OR callHistory.caller_user_id IS NULL)
                LEFT JOIN res_users resUser2 ON (resUser2.id = callHistory.receive_user_id OR callHistory.receive_user_id IS NULL)
        '''

    def _where(self):
        return '''
        '''

    def _group_by(self):
        return '''
            GROUP BY
                callHistory.ods_key,
                callHistory.ods_call_date,
                callHistory.ods_call_only_date,
                callHistory.ods_caller_number,
                callHistory.ods_head_number,
                callHistory.ods_receive_number,
                callHistory.ods_receive_group,
                callHistory.ods_status,
                callHistory.ods_link_file,
                callHistory.ods_type_call,
                callHistory.caller_name,
                callHistory.caller_name,
                callHistory.receive_name,
                callHistory.ods_total_call_time,
                callHistory.ods_real_call_time,
                callHistory.call_content,
                callHistory.caller_partner_id,
                callHistory.caller_user_id,
                callHistory.receive_partner_id,
                callHistory.receive_user_id
        '''


