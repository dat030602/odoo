# -*- coding: utf-8 -*-
"""Initialization for dn_excel_template_rfq_demo."""

import base64
import os
from odoo import api, fields, SUPERUSER_ID

from . import models
from . import wizard


def _seed_rfq_demo_data(env):
    """Seed RFQ Hetian templates (Builder & Python Code) and demo data."""
    po_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
    if not po_model:
        return

    # Locate fixture template file
    template_path = '/opt/odoo19/TEMPLATE_BSK_RFQ_HETIAN_SUMMARY.xlsx'
    if not os.path.exists(template_path):
        template_path = '/opt/odoo19/dev/dn_excel_template_report/tests/fixtures/TEMPLATE_BSK_RFQ_HETIAN_SUMMARY.xlsx'
    if not os.path.exists(template_path):
        return

    with open(template_path, 'rb') as f:
        file_bytes = f.read()

    template_model = env['excel.report.template']

    # 1. Seed RFQ Hetian Summary Template (Visual Builder Mode)
    existing_template = template_model.search([
        ('model_id', '=', po_model.id),
        ('name', '=', 'RFQ Hetian Summary Template')
    ], limit=1)

    template_vals = {
        'name': 'RFQ Hetian Summary Template',
        'model_id': po_model.id,
        'config_mode': 'builder',
        'template_file': base64.b64encode(file_bytes),
        'template_filename': 'TEMPLATE_BSK_RFQ_HETIAN_SUMMARY.xlsx',
        'filename_expr': "'RFQ_%s' % (record.name or 'DRAFT').replace('/', '_')",
        'empty_table_policy': 'keep_blank',
        'variable_ids': [
            (0, 0, {'name': 'date_order', 'code': "format_date(record.date_order) if record.date_order else ''", 'sequence': 10}),
            (0, 0, {'name': 'date_planned', 'code': "format_date(record.date_planned) if record.date_planned else ''", 'sequence': 20}),
            (0, 0, {'name': 'tax_included', 'code': "'Yes' if any(l.tax_ids for l in record.order_line) else 'No'", 'sequence': 30}),
            (0, 0, {'name': 'amount_total', 'code': "record.amount_total", 'sequence': 40}),
            (0, 0, {'name': 'conditions', 'code': "record.conditions or 'Standard Purchase Terms & Conditions'", 'sequence': 50}),
        ],
        'datasource_ids': [
            (0, 0, {
                'name': 'summary',
                'rows_expr': 'record.order_line',
                'column_ids': [
                    (0, 0, {'key': 'product', 'expr': 'line.product_id.display_name or line.name'}),
                    (0, 0, {'key': 'order_number', 'expr': "line.order_number or line.order_id.name or ''"}),
                    (0, 0, {'key': 'design', 'expr': "line.design or 'Standard'"}),
                    (0, 0, {'key': 'quantity', 'expr': 'line.product_qty'}),
                    (0, 0, {'key': 'uom', 'expr': 'line.product_uom_id.name or ""'}),
                    (0, 0, {'key': 'price', 'expr': 'line.price_unit'}),
                    (0, 0, {'key': 'price_subtotal', 'expr': 'line.price_subtotal'}),
                ]
            })
        ]
    }

    if existing_template:
        existing_template.variable_ids.unlink()
        existing_template.datasource_ids.unlink()
        existing_template.write(template_vals)
        template = existing_template
    else:
        template = template_model.create(template_vals)

    try:
        template.action_bind_print_button()
    except Exception:
        pass

    # 2. Seed RFQ Hetian Python Code Template (Python Code Script Mode)
    python_script = """# RFQ Hetian Python Code Report Script
# ==============================================================================
# 1. Custom Scalar Variables for ${var_name}
# ==============================================================================
variables['tax_included'] = 'Yes' if any(l.tax_ids for l in record.order_line) else 'No'
variables['date_order'] = format_date(record.date_order, '%d/%m/%Y')
variables['date_planned'] = format_date(record.date_planned, '%d/%m/%Y')
variables['formatted_date'] = format_date(record.date_order, '%d/%m/%Y')
variables['formatted_datetime'] = format_datetime(record.create_date, '%d/%m/%Y %H:%M')
variables['formatted_total'] = format_amount(record.amount_total, record.currency_id)
variables['amount_total'] = record.amount_total
variables['conditions'] = record.conditions or 'Standard Purchase Terms & Conditions: Net 30 days.'
variables['notes'] = html2plaintext(record.notes or '')

# ==============================================================================
# 2. Table Data Rows for ${table:summary.*}
# ==============================================================================
line_rows = []
for idx, line in enumerate(record.order_line, start=1):
    uom_name = ''
    if hasattr(line, 'product_uom_id') and line.product_uom_id:
        uom_name = line.product_uom_id.name
    elif line.product_id and line.product_id.uom_id:
        uom_name = line.product_id.uom_id.name

    line_rows.append({
        'product': line.name or (line.product_id.display_name if line.product_id else ''),
        'order_number': getattr(line, 'order_number', None) or f"{record.name}-{idx:02d}",
        'design': getattr(line, 'design', None) or 'Standard BSK',
        'quantity': line.product_qty,
        'uom': uom_name or 'Units',
        'price': line.price_unit,
        'price_subtotal': line.price_subtotal,
    })

tables['summary'] = line_rows
"""

    py_template = template_model.search([
        ('model_id', '=', po_model.id),
        ('name', '=', 'RFQ Hetian Python Code Template')
    ], limit=1)

    py_template_vals = {
        'name': 'RFQ Hetian Python Code Template',
        'model_id': po_model.id,
        'config_mode': 'code',
        'template_file': base64.b64encode(file_bytes),
        'template_filename': 'TEMPLATE_BSK_RFQ_HETIAN_SUMMARY.xlsx',
        'filename_expr': "'RFQ_PYTHON_%s' % (record.name or 'DRAFT').replace('/', '_')",
        'empty_table_policy': 'keep_blank',
        'python_code': python_script,
    }

    if py_template:
        py_template.write(py_template_vals)
    else:
        py_template = template_model.create(py_template_vals)

    try:
        py_template.action_bind_print_button()
    except Exception:
        pass
    except Exception:
        pass

    # Seed Vendor
    partner_model = env['res.partner']
    vendor = partner_model.search([('name', '=', 'Hetian Precision Manufacturing Co., Ltd.')], limit=1)
    if not vendor:
        vendor = partner_model.create({
            'name': 'Hetian Precision Manufacturing Co., Ltd.',
            'is_company': True,
            'street': 'No. 88 Jade Valley Industrial Zone, Hetian',
            'email': 'sales@hetian-precision.com',
            'phone': '+86 903 555 8899',
        })

    # Seed Customer
    customer = partner_model.search([('name', '=', 'Global Luxury Jewelry Corp.')], limit=1)
    if not customer:
        customer = partner_model.create({
            'name': 'Global Luxury Jewelry Corp.',
            'is_company': True,
            'street': '450 Fifth Avenue, New York, NY 10018',
            'email': 'procurement@globalluxury.com',
            'phone': '+1 212 555 0199',
            'x_studio_material_quality_standards': (
                "Hetian Grade A Material Specification.\n"
                "Certified ISO 9001:2015 high-density jadeite alloy standard.\n"
                "Optical purity > 99.2%, tolerance limit +/- 0.02mm."
            ),
        })

    # Seed demo products
    prod_model = env['product.product']
    p1 = prod_model.search([('name', '=', 'Hetian White Jade Ring Blank')], limit=1)
    if not p1:
        p1 = prod_model.create({'name': 'Hetian White Jade Ring Blank', 'standard_price': 120.0})
    p2 = prod_model.search([('name', '=', 'Precision Gold Clasp Setting HT-02')], limit=1)
    if not p2:
        p2 = prod_model.create({'name': 'Precision Gold Clasp Setting HT-02', 'standard_price': 45.0})
    p3 = prod_model.search([('name', '=', 'Imperial Jade Seal Mounting Custom')], limit=1)
    if not p3:
        p3 = prod_model.create({'name': 'Imperial Jade Seal Mounting Custom', 'standard_price': 350.0})

    # Seed Demo RFQ with 3 lines
    po_obj = env['purchase.order']
    demo_po = po_obj.search([('partner_id', '=', vendor.id), ('origin', '=', 'HETIAN-DEMO-2026')], limit=1)
    if not demo_po:
        demo_po = po_obj.create({
            'partner_id': vendor.id,
            'origin': 'HETIAN-DEMO-2026',
            'x_studio_order_type': 'Custom Precision Production',
            'x_studio_production_country_1': 'China',
            'x_customer_id': customer.id,
            'conditions': (
                "1. Quality Standards: Strictly adhere to Hetian BSK Specification Rev 3.0.\n"
                "2. Delivery: F.O.B. Shanghai Port within 25 calendar days of order confirmation.\n"
                "3. Warranty: 24 months international warranty against material fatigue.\n"
                "4. Pre-shipment: Third-party metallurgical & gemological certificate required."
            ),
            'note': '<p>Please expedite initial batch inspection before final packaging.</p>',
            'order_line': [
                (0, 0, {
                    'product_id': p1.id,
                    'name': 'Hetian White Jade Ring Blank - Grade A Cut',
                    'order_number': 'ORD-HT-001',
                    'design': 'BSK-HT-SPEC-01A',
                    'product_qty': 150.0,
                    'price_unit': 125.0,
                    'date_planned': fields.Datetime.now(),
                }),
                (0, 0, {
                    'product_id': p2.id,
                    'name': 'Precision Gold Clasp Setting HT-02',
                    'order_number': 'ORD-HT-002',
                    'design': 'BSK-HT-SPEC-02B',
                    'product_qty': 300.0,
                    'price_unit': 48.5,
                    'date_planned': fields.Datetime.now(),
                }),
                (0, 0, {
                    'product_id': p3.id,
                    'name': 'Imperial Jade Seal Mounting Custom',
                    'order_number': 'ORD-HT-003',
                    'design': 'BSK-HT-SPEC-03C',
                    'product_qty': 25.0,
                    'price_unit': 380.0,
                    'date_planned': fields.Datetime.now(),
                }),
            ]
        })


def post_init_hook(env):
    """Seed RFQ Hetian templates and demo data upon module installation."""
    _seed_rfq_demo_data(env)
