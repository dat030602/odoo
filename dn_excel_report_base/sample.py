base64          = _dynamic_import('base64')
io              = _dynamic_import('io')
xlsxwriter      = _dynamic_import('xlsxwriter')
PIL             = _dynamic_import('PIL')
datetime        = _dynamic_import('datetime')
image_data_uri  = _dynamic_import('odoo').tools.image.image_data_uri
image_process   = _dynamic_import('odoo').tools.image.image_process
image_to_base64 = _dynamic_import('odoo').tools.image.image_to_base64
image_data_uri  = _dynamic_import('odoo').tools.image.image_data_uri
html            = _dynamic_import('html')
re              = _dynamic_import('re')
math            = _dynamic_import('math')
tempfile        = _dynamic_import('tempfile')
os              = _dynamic_import('os')

HEADERS = ['No.', 'Picture', 'BSK Number', 'Description', 'ETD', 'Qty', 'Unit Price', 'Subtotal']

# ─────────────────────────────────────────────
# 1. GET DATA
# ─────────────────────────────────────────────
def get_report_data(rec):
    res = []
    uom = ""
    for idx, line in enumerate(rec.order_line.with_context(active_test=False), start=1):
        product_id  = line.with_context(active_test=False).product_id
        image_data  = product_id.image_256 if product_id else False

        picture  = {'type': 'image', 'data': image_data} if image_data else ""

        currency_id = rec.currency_id
        qty = "{:.2f} {}".format(line.product_qty, line.product_uom.name or '') if line.product_qty else "0.00"
        uom = line.product_uom.name or ''
        price_unit = rec.currency_id.format(line.price_unit) if currency_id else line.price_unit or 0
        price_subtotal = rec.currency_id.format(line.price_subtotal) if currency_id else line.price_subtotal or 0

        res.append({
            'type'           : line.display_type,
            'no'             : idx,
            'picture'        : picture,
            'bsk_number'     : line.product_id.x_studio_product_design_id.x_name if line.product_id and line.product_id.x_studio_product_design_id else '',
            'description'    : line.name or '',
            'etd'            : line.date_planned.strftime('%m/%d/%Y') if line.date_planned else '',
            'qty'            : qty,
            'price_unit'     : price_unit,
            'price_subtotal' : price_subtotal,
        })
    total_qty = sum(line.product_qty for line in rec.order_line)
    total_price = sum(line.price_subtotal for line in rec.order_line)
    return {
        'sums': {
            'total_qty'      : "{:.2f} {}".format(total_qty, uom) if total_qty else "0.00",
            'total_price'    : rec.currency_id.format(total_price) if rec.currency_id else total_price,
        },
        'lines': res,
    }

# ─────────────────────────────────────────────
# 2. WORKSHEET SETUP
# ─────────────────────────────────────────────
def setup_worksheet_print(worksheet):
    worksheet.set_paper(9)           # A4
    worksheet.set_portrait()
    worksheet.set_margins(left=0.5, right=0.5, top=1.5, bottom=1)
    worksheet.fit_to_pages(1, 0)

def setup_column_widths(worksheet):
    #  0:No  1:Img  2:BSK Number  3:Description  4:ETD  5:Qty  6:Unit Price  7:Subtotal
    widths = [5, 18, 10, 30, 14, 12, 14, 14, 14, 18]
    for col, w in enumerate(widths):
        worksheet.set_column(col, col, w)

# ─────────────────────────────────────────────
# 3. FORMATS
# ─────────────────────────────────────────────
def prepare_formats(workbook):
    base = {'font_name': 'Arial', 'font_size': 10, 'valign': 'vcenter'}
    f = {}

    f['no_border']          = workbook.add_format({**base})
    f['no_border_address']  = workbook.add_format({**base, 'text_wrap': True})
    f['no_border_bold']     = workbook.add_format({**base, 'bold': True})

    f['title'] = workbook.add_format({**base, 'bold': True, 'font_size': 20, 'valign': 'vcenter',})
    f['label'] = workbook.add_format({**base, 'bold': True})
    f['label_18'] = workbook.add_format({**base, 'bold': True, 'font_size': 18})
    f['value'] = workbook.add_format({**base, 'text_wrap': True})

    f['th'] = workbook.add_format({
        **base, 'bold': True, 'align': 'center', 'valign': 'vcenter',
        'border': 1, 'bg_color': '#D9E1F2', 'text_wrap': True,
    })
    f['td'] = workbook.add_format({
        **base, 'border': 1, 'valign': 'vcenter', 'text_wrap': True,
    })
    f['td_center'] = workbook.add_format({
        **base, 'border': 1, 'align': 'center',
        'valign': 'vcenter', 'text_wrap': True,
    })
    f['td_number'] = workbook.add_format({
        **base, 'border': 1, 'align': 'right',
        'valign': 'vcenter', 'num_format': '#,##0.00', 'text_wrap': True,
    })
    f['footer_label'] = workbook.add_format({
        **base, 'bold': True, 'align': 'right', 'border': 1,
    })
    f['footer_value'] = workbook.add_format({
        **base, 'bold': True, 'align': 'right',
        'border': 1, 'num_format': '#,##0.00', 'text_wrap': True,
    })
    return f

def clean_html(raw_html):
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = re.sub(r'</p>|<br\s*/?>', '\n', text)
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text.strip()

def calculate_notes_height(text, col_width_chars=110, line_height=15):
    if not text:
        return line_height
    lines = text.split('\n')
    total_lines = 0
    for l in lines:
        if not l.strip():
            total_lines += 1
            continue
        total_lines += math.ceil(len(l) / col_width_chars)
    return max(line_height, (total_lines * line_height) + 10)

# ─────────────────────────────────────────────
# 4. WRITE SECTIONS
# ─────────────────────────────────────────────
def render_header(worksheet, formats, current_row, config):
    if not config:
        return current_row
    
    supplier = config.get('supplier', False)
    if supplier:
        worksheet.write(current_row, 0, 'Supplier address:', formats['no_border_bold'])
        current_row += 1
        worksheet.write(current_row, 0, supplier.name or '', formats['no_border_bold'])
        current_row += 1
        worksheet.merge_range(current_row, 0, current_row, len(HEADERS) - 1, supplier.contact_address_complete or '', formats['no_border_address'])
        current_row += 1

    # Title
    current_row += 1
    worksheet.merge_range(current_row, 0, current_row, len(HEADERS) - 1, 'PURCHASE ORDER #%s' % config.get('po_name', ''), formats['title'])
    current_row += 1

    return current_row + 1

def render_body(worksheet, formats, current_row, config):
    if not config:
        return current_row

    pairs = [
        ('Purchase Representative',     'purchase_representative',      'Your Order Reference',         'partner_ref'),
        ('Order Date',                  'order_date',                   'Payment Terms',                'payment_term'),
        ('Currency',                    'currency',                     'Customer Order Number',        'customer_order_number'),
    ]
    for (lbl1, key1, lbl2, key2) in pairs:
        worksheet.write(current_row, 0, lbl1 + ':', formats['label'])
        worksheet.merge_range(current_row, 2, current_row, 3, config.get(key1, ''), formats['value'])
        if lbl2:
            worksheet.write(current_row, 4, lbl2 + ':', formats['label'])
            worksheet.merge_range(current_row, 6, current_row, 7, config.get(key2, ''), formats['value'])
        current_row += 1

    return current_row + 1

def _insert_image(worksheet, row, col, image_data, scale=None, max_x=None, max_y=None):
    """
    Flexible helper function to decode base64 image data and insert it into a worksheet
    or return the image stream for header/footer configuration.
    """
    if not image_data:
        return None, None

    if scale is None:
        scale = {'x_scale': 0.45, 'y_scale': 0.45}
    else:
        scale = dict(scale)

    try:
        # Decode base64 image to BytesIO stream
        img_bytes = base64.b64decode(image_data)
        img_stream = io.BytesIO(img_bytes)

        # Scale down image dimensions dynamically if maximum bounds are provided
        if max_y or max_x:
            img = PIL.Image.open(img_stream)
            orig_width, orig_height = img.size
            img_stream.seek(0)  # Reset stream position after reading image size

            x_scale = scale.get('x_scale', 1.0)
            y_scale = scale.get('y_scale', 1.0)

            curr_width = orig_width * x_scale
            curr_height = orig_height * y_scale

            # Adjust scale based on maximum allowed height
            if max_y and curr_height > max_y:
                ratio = max_y / curr_height
                x_scale *= ratio
                y_scale *= ratio

            # Adjust scale based on maximum allowed width
            if max_x and (orig_width * x_scale) > max_x:
                ratio = max_x / (orig_width * x_scale)
                x_scale *= ratio
                y_scale *= ratio

            scale['x_scale'] = x_scale
            scale['y_scale'] = y_scale

        # Insert image directly into worksheet if instance is provided
        if worksheet is not None:
            worksheet.insert_image(row, col, 'img.png', {
                'image_data': img_stream,
                'x_offset': 4,
                'y_offset': 4,
                'object_position': 1,
                **scale,
            })

        return img_stream, scale

    except Exception:
        # Silently pass errors to prevent server action execution crashes
        pass

    return None, None

def process_header_logo(image_data, target_height_px=50):
    """
    Decodes base64 image, resizes it physically using PIL, 
    and saves it to a TEMPORARY FILE on disk for XlsxWriter set_header.
    """
    if not image_data:
        return None

    try:
        img_bytes = base64.b64decode(image_data)
        img_stream = io.BytesIO(img_bytes)

        img = PIL.Image.open(img_stream)
        orig_width, orig_height = img.size

        if orig_height > target_height_px:
            ratio = target_height_px / float(orig_height)
            new_width = max(1, int(orig_width * ratio))
            new_height = target_height_px

            resample_mode = None
            try:
                resample_mode = PIL.Image.Resampling.LANCZOS
            except Exception:
                try:
                    resample_mode = PIL.Image.LANCZOS
                except Exception:
                    resample_mode = PIL.Image.ANTIALIAS

            img = img.resize((new_width, new_height), resample_mode)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, format='PNG')
        temp_file.close()

        return temp_file.name

    except Exception as e:
        log("Error processing header logo: %s" % str(e))
        pass

    return None

def render_table(worksheet, formats, current_row, config, data_records):
    if not config:
        return current_row

    # ── Table header row ──
    for col, h in enumerate(HEADERS):
        worksheet.write(current_row, col, h, formats['th'])
    worksheet.set_row(current_row, 30)
    current_row += 1

    # ── Data rows ──
    for record in data_records.get('lines', []):
        worksheet.set_row(current_row, 65)

        worksheet.write(current_row, 0, record.get('no', ''),           formats['td_center'])

        # Column 1 – product image
        picture = record.get('picture', '')
        if picture and isinstance(picture, dict) and picture.get('data'):
            _insert_image(worksheet, current_row, 1, picture['data'], max_x=180, max_y=80)
        worksheet.write(current_row, 1, '',  formats['td'])

        worksheet.write(current_row, 2, record.get('bsk_number', ''),  formats['td_center'])
        worksheet.write(current_row, 3, record.get('description', ''),  formats['td'])
        worksheet.write(current_row, 4, record.get('etd', ''),          formats['td_center'])
        worksheet.write(current_row, 5, record.get('qty', 0),           formats['td_number'])
        worksheet.write(current_row, 6, record.get('price_unit', 0),    formats['td_number'])
        worksheet.write(current_row, 7, record.get('price_subtotal', 0),formats['td_number'])

        current_row += 1

    # ── Total row ──
    worksheet.merge_range(current_row, 0, current_row, 4, 'Total', formats['footer_label'])
    worksheet.write(current_row, 5, data_records.get('sums', {}).get('total_qty', 0), formats['footer_value'])
    worksheet.write(current_row, 6, '', formats['footer_label'])
    worksheet.write(current_row, 7, data_records.get('sums', {}).get('total_price', 0), formats['footer_value'])

    return current_row

def render_footer(worksheet, formats, current_row, config):
    if not config:
        return current_row

    current_row += 1

    sections = [
        ('', 'notes'),
        ('Quality Standards:', 'x_studio_quality_standards'),
        ('Production Requirements:', 'x_production_requirements'),
    ]

    for label, key in sections:
        current_row += 1
        content = config.get(key, '')
        if not content:
            continue

        if label:
            worksheet.write(current_row, 0, label, formats['label_18'])
            current_row += 1

        lines = content.split('\n')
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            line_height = max(16, (len(line_str) // 110 + 1) * 14)
            worksheet.set_row(current_row, line_height)
            worksheet.merge_range(current_row, 0, current_row, len(HEADERS) - 1, line_str, formats['no_border_address'])
            current_row += 1

    return current_row

def setup_footer(worksheet):
    footer_text = (
        '&C&"Arial,Bold"BSK SUPPLY CO., LIMITED\n'
        'Bank: DBS Bank (Hong Kong) Ltd.\n'
        'Acc no.: 7949855491\n'
        'SWIFT: DHBKHKHH'
        'Bank code: 016 | Branch: 478'
        '&R&"Arial,Regular"Page &P of &N'
    )
    worksheet.set_footer(footer_text)

def setup_header(worksheet, company_logo_data=None):
    header_text = (
        '&L&G\n'
        '&"Arial,Bold"BSK Supply Co., Ltd HK\n'
        'UNIT A7, 12/F ASTORIA BUILDING\n'
        '34 ASHLEY ROAD TSIM SHA TSUI\n'
        'HONG KONG\n'
    )

    header_options = {}
    temp_logo_path = None

    if company_logo_data:
        try:
            temp_logo_path = process_header_logo(company_logo_data, target_height_px=50)
            if temp_logo_path:
                header_options['image_left'] = temp_logo_path
        except Exception as e:
            log("Error processing header logo: %s" % str(e))
            pass

    worksheet.set_header(header_text, header_options)
    return temp_logo_path

def render_signature(worksheet, formats, current_row, config):
    if not config:
        return current_row
    current_row += 2
    worksheet.write(current_row, 7, config.get('sign', ''), formats['no_border_bold'])
    return current_row + 1

# ─────────────────────────────────────────────
# 5. GENERATE EXCEL FILE
# ─────────────────────────────────────────────
def generate_excel_file(rec):
    output    = io.BytesIO()
    workbook  = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Purchase Order')

    setup_worksheet_print(worksheet)
    setup_column_widths(worksheet)

    formats      = prepare_formats(workbook)
    data_records = get_report_data(rec)

    # ── Build configs ──

    header_config = {
        'company'        : rec.company_id,
        'supplier'       : rec.partner_id,
        'po_name'        : rec.name,
    }

    body_config = {
        'purchase_representative' : rec.user_id.name or '',
        'partner_ref'              : rec.partner_ref or '',
        'order_date'              : rec.date_approve.strftime('%m/%d/%Y') if rec.date_approve else '',
        'payment_term'            : rec.payment_term_id.name or '',
        'currency'                : rec.currency_id.name or '',
        'customer_order_number'   : rec.partner_ref or '',
    }

    table_config = True

    footer_config = {
        'notes' : clean_html(rec.notes) if rec.notes else "",
        'x_studio_quality_standards' : rec.x_studio_quality_standards or "",
        'x_production_requirements' : rec.x_production_requirements or "",
    }

    signature_config = {}

    setup_header(worksheet, rec.company_id.logo if rec.company_id else None)
    setup_footer(worksheet)

    # ── Write all sections ──
    current_row = 0
    current_row = render_header(worksheet, formats, current_row, header_config)
    current_row = render_body(worksheet, formats, current_row, body_config)
    current_row = render_table(worksheet, formats, current_row, table_config, data_records)
    current_row = render_footer(worksheet, formats, current_row, footer_config)
    current_row = render_signature(worksheet, formats, current_row, signature_config)

    workbook.close()
    output.seek(0)
    return output.read()

# ─────────────────────────────────────────────
# 6. DOWNLOAD ACTION
# ─────────────────────────────────────────────
def execute_download_action(rec):
    excel_data   = generate_excel_file(rec)
    excel_base64 = base64.b64encode(excel_data)

    current_time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name  = rec.name.replace('/', '_') if rec.name else 'PO'
    file_name  = "Purchase_Order_{}_{}.xlsx".format(safe_name, current_time_str)

    attachment = env['ir.attachment'].create({
        'name'      : file_name,
        'type'      : 'binary',
        'datas'     : excel_base64,
        'res_model' : 'purchase.order',
        'res_id'    : rec.id,
    })

    return {
        'type'  : 'ir.actions.act_url',
        'url'   : '/web/content/%s?download=true' % attachment.id,
        'target': 'self',
    }

# ─────────────────────────────────────────────
# 7. ENTRY POINT
# ─────────────────────────────────────────────
for rec in records:
    action = execute_download_action(rec)
