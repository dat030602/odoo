import re
import sys
import json
import ast
import logging
import random
import io
import hashlib
import hmac
import urllib
import base64
import requests
import xmlrpc.client
import http.client
import socket

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ApprovalWorkflowConfig(models.Model):
    _name = "approval.workflow.config"
    _description = "Approval Workflow Configuration"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    category_id = fields.Many2one("approval.category", string="Approval Category", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Target Model", required=True, ondelete="cascade")
    technical_name = fields.Char(string="Technical Name", required=True, help="Used for generated objects (views, actions, menus)")
    technical_name_prefix = fields.Char(string="Technical Name Prefix", compute="_compute_technical_name_prefix", store=True)
    active = fields.Boolean(string="Active", default=True)
    stage_ids = fields.One2many("approval.workflow.stage", "workflow_id", string="Workflow Stages")

    server_id = fields.Many2one("ir.actions.server", string="Server Action", readonly=True)
    action_id = fields.Many2one("ir.actions.act_window", string="Action", readonly=True)
    menu_id = fields.Many2one("ir.ui.menu", string="Menu", readonly=True)
    list_view_id = fields.Many2one("ir.ui.view", string="List View", readonly=True)
    form_view_id = fields.Many2one("ir.ui.view", string="Form View", readonly=True)

    state = fields.Selection(
        [("draft", "Draft"), ("locked", "Locked")],
        string="State",
        default="draft",
        help="Locked state means the workflow is active and cannot be edited. To make changes, you need to archive the workflow and create a new one.",
    )

    # Python Code Execution for Initialization
    init_code = fields.Text(
        string="Initialization Python Code",
        help="Python code to execute when creating an approval request to initialize data. "
             "Available variables: record (the approval.request record), env, user. "
             "Use 'record' to modify the approval request fields.",
    )

    def default_get(self, fields):
        res = super().default_get(fields)

        default_code = """
# Begin: Do not remove
src_id = 1 # Replace with the actual approval.workflow.config ID
config_id = env['approval.workflow.config'].sudo().browse(src_id)
if not config_id.exists():
    raise UserError(f"Approval config with id {src_id} not found.")
action = config_id.sudo().action_id
if not action:
    raise UserError(f"Approval config with id {src_id} has no associated action.")

vals = {
    'request_owner_id': env.user.id,
    'category_id': config_id.category_id.id,
}

if config_id.category_id and not config_id.category_id.automated_sequence:
    vals['name'] = "%s - %s - %s" % (
        config_id.name,
        "Approval Request",
        record.display_name
    )

request_id = env['approval.request'].create(vals)

# End: Do not remove

# Begin: Write code here

request_id['date'] = datetime.datetime.now()
request_id['reason'] = 'This is a custom reason for the approval request.'

# End: Write code here

# Begin: Do not remove
action = action.sudo().read()[0]
action['views'] = [(config_id.sudo().form_view_id.id, 'form')]
action['res_id'] = request_id.id

# End: Do not remove
"""
        res['init_code'] = default_code
        return res

    @api.constrains("technical_name")
    def _check_technical_name(self):
        pattern = r"^[A-Za-z0-9_]+$"
        for rec in self:
            if rec.technical_name and not re.match(pattern, rec.technical_name):
                raise ValidationError(_("Technical Name only allows letters, numbers and underscore (_)"))

    @api.constrains("category_id")
    def _check_category_unique(self):
        for rec in self:
            if rec.category_id:
                existing = self.search(
                    [
                        ("category_id", "=", rec.category_id.id),
                        ("id", "!=", rec.id),
                    ],
                )
                if existing:
                    raise ValidationError(
                        _(
                            "Approval Category can only have one Workflow Configuration. "
                            "Category '%s' already has workflow '%s'.",
                        )
                        % (rec.category_id.name, existing[0].name),
                    )


    @api.depends("technical_name")
    def _compute_technical_name_prefix(self):
        for rec in self:
            rec.technical_name_prefix = ("approval_%s" % rec.technical_name) if rec.technical_name else ""

    def action_generate_views(self):
        for rec in self:
            rec._generate_form_view()
            rec._generate_tree_view()
            rec._generate_action()
            rec._generate_menu()

    def action_create_server_action(self):
        for rec in self:
            if not rec.server_id:
                server_action = self.env["ir.actions.server"].create(
                    {
                        "name": "[%s] Send Approval" % self.name,
                        "model_id": rec.model_id.id,
                        "state": "code",
                        "code": rec.init_code or "# Python code to initialize approval request data\n# Available variables: record, env, user\n# Example:\n# record.name = 'Custom Name'\n# record.description = 'Auto-generated description'",
                    },
                )
                rec.server_id = server_action

    def action_open_server_action(self):
        return {
            "name": "Server Action",
            "type": "ir.actions.act_window",
            "res_model": "ir.actions.server",
            "res_id": self.server_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("init_code")
    def _onchange_init_code(self):
        for rec in self:
            if rec.init_code and rec.server_id:
                rec.server_id.code = rec.init_code
    
    @api.onchange("name")
    def _onchange_name(self):
        for rec in self:
            if rec.name:
                # Update menu name if exists
                if rec.menu_id:
                    rec.menu_id.name = rec.name
                # Update action name if exists
                if rec.action_id:
                    rec.action_id.name = rec.name
                # Update server action name if exists
                if rec.server_id:
                    rec.server_id.name = "[%s] Send Approval" % rec.name
                
                if rec.menu_id:
                    rec.menu_id.name = rec.name

                if rec.category_id:
                    rec.category_id.name = rec.name

    def _generate_form_view(self):
        view_xml = f"""
        <form string="{self.name}">
            <header>
                <button name="action_custom_approve" string="Send for Approval" type="object" class="btn-primary" invisible="custom_request_status != 'new'"/>
                <button name="action_custom_approve" string="Approve" type="object" class="btn-primary" invisible="not can_click_approval or custom_request_status != 'pending'"/>
                <button name="advanced_dynamic_approval.action_approval_reason_wizard" string="Reject" type="action" class="btn-danger" context="{'default_approval_request_id': id, 'default_action': 'reject'}" invisible="not can_click_approval or custom_request_status != 'pending'"/>
                <button name="advanced_dynamic_approval.action_approval_reason_wizard" string="Cancel" type="action" class="btn-secondary" context="{'default_approval_request_id': id, 'default_action': 'cancel'}" invisible="custom_request_status in ['cancel', 'approved']"/>
                <field name="custom_request_status" widget="statusbar" statusbar_visible="new,pending,approved"/>
            </header>
            <sheet>
                <div class="d-flex justify-content-between align-items-center">
                    <h1 class="flex-grow-1">
                        <field name="name" placeholder="e.g. Approval Workflow" readonly="1"/>
                    </h1>
                </div>
                <group>
                    <field name="request_owner_id" readonly="custom_request_status != 'new'"/>
                    <field name="category_id" readonly="custom_request_status != 'new'"/>
                    <field name="date" readonly="custom_request_status != 'new'"/>
                </group>
                <notebook>
                    <page string="Description" name="description">
                        <field name="reason" readonly="custom_request_status != 'new'"/>
                    </page>
                    <page string="Approval History" name="approval_history">
                        <field name="approval_history_ids" readonly="1"/>
                    </page>
                </notebook>
            </sheet>
            <chatter/>
        </form>
        """
        self.form_view_id = self.env["ir.ui.view"].create(
            {
                "name": f"{self.technical_name_prefix}_form",
                "type": "form",
                "model": "approval.request",
                "arch": view_xml,
                "active": True,
            },
        )

    def _generate_tree_view(self):
        view_xml = f"""
        <list string="{self.name}">
            <field name="name"/>
            <field name="request_owner_id"/>
            <field name="category_id"/>
            <field name="date"/>
            <field name="request_status" widget="badge" decoration-info="request_status == 'new'" decoration-warning="request_status == 'pending'" decoration-success="request_status == 'approved'" decoration-danger="request_status in ['refused', 'cancel']"/>
        </list>
        """
        self.list_view_id = self.env["ir.ui.view"].create(
            {
                "name": f"{self.technical_name_prefix}_list",
                "type": "list",
                "model": "approval.request",
                "arch": view_xml,
                "active": True,
            },
        )

    def _generate_action(self):
        form_view = self.env["ir.ui.view"].search([("name", "=", f"{self.technical_name_prefix}_form")], limit=1)
        list_view = self.env["ir.ui.view"].search([("name", "=", f"{self.technical_name_prefix}_list")], limit=1)

        self.action_id = self.env["ir.actions.act_window"].create(
            {
                "name": self.name,
                "type": "ir.actions.act_window",
                "res_model": "approval.request",
                "view_mode": "list,form",
                "view_ids": [
                    (0, 0, {"view_mode": "list", "view_id": list_view.id}),
                    (0, 0, {"view_mode": "form", "view_id": form_view.id}),
                ],
                "domain": [("category_id", "=", self.category_id.id)],
                "context": {"default_category_id": self.category_id.id},
            },
        )

    def _generate_menu(self):
        parent_menu = self.env.ref("approvals.approvals_menu_manager", raise_if_not_found=False)

        if parent_menu and self.action_id:
            self.menu_id = self.env["ir.ui.menu"].create(
                {
                    "name": self.name,
                    "parent_id": parent_menu.id,
                    "action": f"ir.actions.act_window,{self.action_id.id}",
                    "sequence": 10,
                },
            )

    def action_open_stages(self):
        self.ensure_one()
        action = self.env.ref('advanced_dynamic_approval.approval_workflow_stage_action').sudo().read()[0]
        action['domain'] = [('workflow_id', '=', self.id)]
        action['context'] = {'default_workflow_id': self.id}
        return action

    def unlink(self):
        for rec in self:
            if rec.state == "locked":
                raise UserError(_("Cannot delete a locked workflow configuration. Please archive it instead."))
            records = self.env["approval.request"].search([("category_id", "=", rec.category_id.id)])
            if records:
                raise UserError(_("Cannot delete workflow configuration '%s' because there are existing approval requests associated with its category." % rec.name))
            rec.server_id.unlink()
            rec.action_id.unlink()
            rec.menu_id.unlink()
            rec.list_view_id.unlink()
            rec.form_view_id.unlink()
        return super().unlink()
