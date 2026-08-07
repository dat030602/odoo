"""
Connector Schema Builder
========================
Service that applies discovered schema by creating ir.model, ir.model.fields,
ir.model.relation, and views. Runs only after discovery is complete.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ConnectorSchemaBuilder(models.AbstractModel):
    """Service for applying discovered schema to the Odoo database.

    Creates dynamic models, fields, relations, and views based on the
    schema discovered from raw JSON responses. This service should only
    be called after discovery is complete for all signatures.
    """

    _name = "connector.schema.builder"
    _description = "Service for applying discovered schema"

    def apply_schema(self, discovered):
        """Apply the discovered schema by creating models, fields, and views.

        :param discovered: A dict with 'models', 'fields', and 'relations' lists.
        """
        model_cache = {}
        for m in discovered["models"]:
            model_cache[m["name"]] = self._get_or_create_model(m["name"])

        for f in discovered["fields"]:
            self._get_or_create_field(model_cache[f["model"]], f["name"], f["type"])

        for r in discovered["relations"]:
            self._get_or_create_relation(
                model_cache[r["parent"]], model_cache[r["child"]], r["type"]
            )

        self._generate_views(model_cache)
        self.env.registry.setup_models(self.env.cr)

    def _get_or_create_model(self, name):
        """Get an existing model or create a new one with default fields.

        Creates the model with x_payload (Text) and x_external_id (Char)
        fields, and sets up access rights for the connector developer group.

        :param name: The model name (e.g., 'x_shopify_order').
        :return: The ir.model record for the created or existing model.
        """
        IrModel = self.env["ir.model"].sudo()
        existing = IrModel.search([("model", "=", name)], limit=1)
        if existing:
            return existing
        model = IrModel.create({
            "name": name,
            "model": name,
            "state": "manual",
        })
        self.env["ir.model.fields"].sudo().create([
            {
                "model_id": model.id,
                "name": "x_payload",
                "field_description": "Raw Payload",
                "ttype": "text",
            },
            {
                "model_id": model.id,
                "name": "x_external_id",
                "field_description": "External ID",
                "ttype": "char",
            },
        ])
        self._create_access_rights(model)
        return model

    def _create_access_rights(self, model):
        """Create access rights for a dynamically created model.

        Grants full CRUD permissions to the connector developer group.

        :param model: The ir.model record to create access rights for.
        """
        self.env["ir.model.access"].sudo().create({
            "name": f"access_{model.model}_connector",
            "model_id": model.id,
            "group_id": self.env.ref(
                "connector_base.group_connector_developer"
            ).id,
            "perm_read": 1,
            "perm_write": 1,
            "perm_create": 1,
            "perm_unlink": 1,
        })

    def _get_or_create_field(self, model, name, ttype):
        """Get an existing field or create a new one on the given model.

        All fields are created as Text type following the raw-data-first
        philosophy. Business logic handles type conversion later.

        :param model: The ir.model record to add the field to.
        :param name: The field name (e.g., 'x_price').
        :param ttype: The field type (always 'text' in this framework).
        :return: The ir.model.fields record.
        """
        IrField = self.env["ir.model.fields"].sudo()
        existing = IrField.search([
            ("model_id", "=", model.id),
            ("name", "=", name),
        ], limit=1)
        if existing:
            return existing
        return IrField.create({
            "model_id": model.id,
            "name": name,
            "field_description": name.replace("x_", "").replace("_", " ").title(),
            "ttype": "text",
        })

    def _get_or_create_relation(self, parent_model, child_model, rel_type):
        """Create a One2many/Many2one relation between parent and child models.

        Creates a Many2one field on the child model pointing to the parent,
        and a One2many field on the parent model pointing back to the child.

        :param parent_model: The ir.model record for the parent model.
        :param child_model: The ir.model record for the child model.
        :param rel_type: The relation type (currently only 'one2many' supported).
        """
        IrField = self.env["ir.model.fields"].sudo()
        m2o_name = f"x_{parent_model.model}_id"
        if not IrField.search([
            ("model_id", "=", child_model.id),
            ("name", "=", m2o_name),
        ]):
            IrField.create({
                "model_id": child_model.id,
                "name": m2o_name,
                "field_description": "Parent",
                "ttype": "many2one",
                "relation": parent_model.model,
                "ondelete": "cascade",
            })
        o2m_name = f"x_{child_model.model.split('_')[-1]}_ids"
        if not IrField.search([
            ("model_id", "=", parent_model.id),
            ("name", "=", o2m_name),
        ]):
            IrField.create({
                "model_id": parent_model.id,
                "name": o2m_name,
                "field_description": "Lines",
                "ttype": "one2many",
                "relation": child_model.model,
                "relation_field": m2o_name,
            })

    def _generate_views(self, model_cache):
        """Generate form and list views for all models in the cache.

        :param model_cache: A dict mapping model names to ir.model records.
        """
        for model in model_cache.values():
            self._generate_list_view(model)
            self._generate_form_view(model)

    def _generate_list_view(self, model):
        """Generate a list view for the given model.

        Shows all non-One2many fields. The first 5 fields are shown by
        default; the rest are hidden and can be toggled by the user.

        :param model: The ir.model record to generate a list view for.
        """
        fields_ = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("ttype", "!=", "one2many"),
        ])
        arch_fields = []
        for i, f in enumerate(fields_):
            optional = "show" if i < 5 else "hide"
            arch_fields.append(
                f'<field name="{f.name}" optional="{optional}"/>'
            )
        arch = f'<list>{"".join(arch_fields)}</list>'
        self._create_or_update_view(model, "list", arch)

    def _generate_form_view(self, model):
        """Generate a form view for the given model.

        Displays own fields in a group and child One2many relations in
        a notebook with one page per relation.

        :param model: The ir.model record to generate a form view for.
        """
        own_fields = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("ttype", "not in", ["one2many"]),
        ])
        child_o2m = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("ttype", "=", "one2many"),
        ])
        group_fields = "".join(
            f'<field name="{f.name}"/>' for f in own_fields
        )
        notebook_pages = "".join(
            f'<page string="{f.field_description}">'
            f'<field name="{f.name}">'
            f'<list editable="bottom"></list>'
            f'</field></page>'
            for f in child_o2m
        )
        arch = (
            f'<form><sheet><group>{group_fields}</group>'
            f'<notebook>{notebook_pages}</notebook></sheet></form>'
        )
        self._create_or_update_view(model, "form", arch)

    def _create_or_update_view(self, model, view_type, arch):
        """Create or update a view for the given model and view type.

        :param model: The ir.model record.
        :param view_type: The view type ('list' or 'form').
        :param arch: The view architecture XML string.
        """
        IrUiView = self.env["ir.ui.view"].sudo()
        existing = IrUiView.search([
            ("model", "=", model.model),
            ("type", "=", view_type),
            ("name", "=", f"view_{model.model}_{view_type}_connector"),
        ], limit=1)
        vals = {
            "name": f"view_{model.model}_{view_type}_connector",
            "model": model.model,
            "type": view_type,
            "arch": arch,
            "priority": 10,
        }
        if existing:
            existing.write(vals)
        else:
            IrUiView.create(vals)
